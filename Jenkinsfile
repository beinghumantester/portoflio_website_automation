// Jenkins Pipeline for the portfolio website automation suite.
// Now runs against a Selenium Grid (hub + Chrome/Firefox nodes) instead
// of a browser bundled inside the test image - Deployment Job builds the
// lean test image, Execution Job constructs the test command, and
// Run Tests brings up the whole Grid + test-runner stack via Docker Compose.
//
// Prerequisites on the Jenkins server itself:
//   - Docker + Docker Compose installed, Jenkins user able to run both
//   - "HTML Publisher" plugin and "Allure Jenkins Plugin" installed
//   - An "Allure Commandline" tool configured under Manage Jenkins -> Tools

pipeline {
    agent any

    options {
        // This Jenkinsfile is shared by two separate jobs (the regular
        // 'portfolio-automation' Pipeline and the 'portfolio-automation-pr'
        // Multibranch Pipeline). Both start a Selenium Grid bound to the
        // same fixed host ports (4442-4444) - if they ever ran at the same
        // time, they'd collide (confirmed: this already happened once as
        // a container-name conflict, and would recur as a port-binding
        // conflict even after that specific fix). This lock ensures only
        // one build, from either job, holds the Grid at a time - the
        // other waits in queue instead of failing.
        lock(resource: 'selenium-grid-ports')
    }

    parameters {
        string(
            name: 'BASE_URL',
            defaultValue: 'https://beinghumantester.com',
            description: 'URL of the portfolio site to test against'
        )
        string(
            name: 'TEST_MARKER',
            defaultValue: '',
            description: 'Optional pytest marker to run a subset (navigation, links, modal). Leave blank for the full suite.'
        )
        choice(
            name: 'BROWSER',
            choices: ['chrome', 'firefox'],
            description: 'Which Grid node to run against'
        )
        string(
            name: 'NOTIFY_EMAIL',
            defaultValue: 'thebeinghumantester@gmail.com',
            description: 'Email address for build result notifications. Leave blank to skip.'
        )
    }

    environment {
        IMAGE_NAME = 'portfolio-automation'
        IMAGE_TAG = "${env.BUILD_NUMBER}"
        // Explicitly derived from params (with a safe fallback), rather
        // than relying on Jenkins auto-injecting parameters into the shell
        // environment. Confirmed via console output: on a Multibranch
        // job's very first build for a newly-discovered branch, the
        // parameter genuinely isn't available yet (Jenkins is still in
        // the middle of discovering it from this same Jenkinsfile) -
        // ${BASE_URL} in shell steps came through completely empty,
        // breaking curl. This affects every new branch/PR going forward,
        // not just this one - environment{} block entries are evaluated
        // as plain Groovy at pipeline load time and don't have this
        // timing problem.
        BASE_URL = "${params.BASE_URL ?: 'https://beinghumantester.com'}"
        BROWSER = "${params.BROWSER ?: 'chrome'}"
    }

    stages {
        stage('Checkout') {
            steps {
                checkout scm
            }
        }

        stage('Prepare') {
            parallel {
                stage('Deployment Job') {
                    steps {
                        echo "Deployment job: building test image, tagged :${IMAGE_TAG} and :latest."
                        sh '''
                            docker build --no-cache \
                                -t ${IMAGE_NAME}:${IMAGE_TAG} \
                                -t ${IMAGE_NAME}:latest \
                                .
                        '''
                    }
                }
                stage('Execution Job') {
                    steps {
                        echo 'Execution job: calling the execution API to construct the test command.'
                        sh '''
                            TEST_MARKER="${TEST_MARKER}" COMMAND_OUTPUT_FILE=docker_run_args.txt \
                                python3 execution_api/build_command.py
                        '''
                    }
                }
            }
        }

        stage('Push Image') {
            steps {
                // Pushes to GitHub Container Registry (ghcr.io) - free,
                // no card required, and reuses the same GitHub account
                // this repo already lives on. Requires a Jenkins
                // credential named 'ghcr-credentials' (Username with
                // password: GitHub username + a PAT with write:packages).
                withCredentials([usernamePassword(
                    credentialsId: 'ghcr-credentials',
                    usernameVariable: 'GHCR_USER',
                    passwordVariable: 'GHCR_TOKEN'
                )]) {
                    sh '''
                        docker tag ${IMAGE_NAME}:${IMAGE_TAG} ghcr.io/${GHCR_USER}/${IMAGE_NAME}:${IMAGE_TAG}
                        docker tag ${IMAGE_NAME}:latest ghcr.io/${GHCR_USER}/${IMAGE_NAME}:latest

                        # Re-login fresh before each push and retry on
                        # failure - confirmed from a real run that the
                        # first push can succeed while a second push,
                        # seconds later in the same session, fails with
                        # "unauthorized". Re-authenticating per push and
                        # retrying rules out a stale/expired session token
                        # as the cause, without needing to be 100% certain
                        # that's the exact mechanism.
                        push_with_retry() {
                            image="$1"
                            for attempt in 1 2 3; do
                                echo "$GHCR_TOKEN" | docker login ghcr.io -u "$GHCR_USER" --password-stdin
                                if docker push "$image"; then
                                    return 0
                                fi
                                echo "Push failed (attempt ${attempt}/3) for ${image}, retrying in 5s..."
                                sleep 5
                            done
                            echo "Push failed after 3 attempts: ${image}"
                            return 1
                        }

                        push_with_retry ghcr.io/${GHCR_USER}/${IMAGE_NAME}:${IMAGE_TAG}
                        push_with_retry ghcr.io/${GHCR_USER}/${IMAGE_NAME}:latest
                        docker logout ghcr.io
                    '''
                }
            }
        }

        stage('Security Scan') {
            steps {
                // Trivy: free, open-source vulnerability scanner (Aqua
                // Security). Scans OS packages and Python dependencies in
                // the image we just built for known CVEs.
                //
                // --severity CRITICAL,HIGH filters out noise from LOW/
                // MEDIUM findings, which are common and rarely urgent.
                //
                // --exit-code 0 means: report findings, but never fail
                // the build - deliberately lenient for this first rollout,
                // since we don't have a baseline yet of how many findings
                // a typical scan turns up. Once you've seen a real report,
                // tighten this to --exit-code 1 to actually block builds
                // on CRITICAL findings.
                //
                // The docker.sock mount lets Trivy inspect the image
                // directly from the local Docker daemon - no need to
                // export/re-pull it. The cache volume avoids re-downloading
                // Trivy's vulnerability database on every single build.
                sh '''
                    docker run --rm \
                        -v /var/run/docker.sock:/var/run/docker.sock \
                        -v trivy-cache:/root/.cache/ \
                        aquasec/trivy:latest image \
                        --severity CRITICAL,HIGH \
                        --exit-code 0 \
                        ${IMAGE_NAME}:${IMAGE_TAG}
                '''
            }
        }

        stage('Health Check') {
            steps {
                sh '''
                    echo "Checking portfolio site is reachable..."
                    SITE_STATUS=$(curl -s -o /dev/null -w "%{http_code}" --max-time 10 "${BASE_URL}" || echo "000")
                    if [ "$SITE_STATUS" -lt 200 ] || [ "$SITE_STATUS" -ge 400 ]; then
                        echo "Site health check FAILED - got HTTP ${SITE_STATUS} from ${BASE_URL}"
                        exit 1
                    fi
                    echo "Site is reachable (HTTP ${SITE_STATUS})"

                    echo "Starting Selenium Grid..."
                    export HOST_UID=$(id -u)
                    export HOST_GID=$(id -g)
                    export IMAGE_NAME="${IMAGE_NAME}"
                    export IMAGE_TAG="${IMAGE_TAG}"
                    docker compose up -d selenium-hub chrome-node firefox-node

                    echo "Waiting for Grid hub to report ready..."
                    GRID_READY=""
                    for i in $(seq 1 15); do
                        HUB_RESPONSE=$(curl -s http://localhost:4444/status || true)
                        echo "Hub response: ${HUB_RESPONSE}"
                        GRID_READY=$(echo "${HUB_RESPONSE}" | grep -oE '"ready":[[:space:]]*true' || true)
                        if [ -n "$GRID_READY" ]; then
                            echo "Selenium Grid is ready."
                            break
                        fi
                        echo "Grid not ready yet, waiting... (${i}/15)"
                        sleep 2
                    done
                    if [ -z "$GRID_READY" ]; then
                        echo "Selenium Grid did not become ready in time - aborting."
                        docker compose down -v
                        exit 1
                    fi
                '''
            }
        }

        stage('Run Tests') {
            steps {
                sh '''
                    # Clear out any leftover root-owned files from earlier
                    # runs (before the HOST_UID/HOST_GID fix was in place).
                    # Jenkins' own user can't delete root-owned files, but a
                    # disposable root container can, via the same bind mount.
                    mkdir -p reports
                    docker run --rm -v "${WORKSPACE}/reports:/reports" alpine sh -c "rm -rf /reports/* /reports/.[!.]* 2>/dev/null || true"

                    export HOST_UID=$(id -u)
                    export HOST_GID=$(id -g)
                    export BASE_URL="${BASE_URL}"
                    export BROWSER="${BROWSER}"
                    export IMAGE_NAME="${IMAGE_NAME}"
                    export IMAGE_TAG="${IMAGE_TAG}"
                    DOCKER_RUN_ARGS=$(cat docker_run_args.txt)
                    echo "Running with args: '${DOCKER_RUN_ARGS}'"

                    docker compose run --rm tests ${DOCKER_RUN_ARGS}
                    TEST_EXIT_CODE=$?
                    docker compose down -v
                    exit $TEST_EXIT_CODE
                '''
            }
        }
    }

    post {
        always {
            sh 'docker compose down -v || true'
            sh 'docker image prune -f || true'
            script {
                // currentBuild.testResultAction is blocked by this Jenkins
                // instance's script-security sandbox entirely (confirmed:
                // it throws MissingPropertyException even on builds with
                // real, successful test results, not just empty ones).
                // The junit step's own return value doesn't have this
                // problem - it's a plain object handed back from an
                // already-approved step, not a dig into internal Run
                // fields, so reading its properties needs no approval.
                def results = junit(testResults: 'reports/junit.xml', allowEmptyResults: true)
                env.TEST_TOTAL = "${results.totalCount}"
                env.TEST_FAIL = "${results.failCount}"
                env.TEST_SKIP = "${results.skipCount}"
                env.TEST_PASS = "${results.totalCount - results.failCount - results.skipCount}"
            }
            publishHTML(target: [
                allowMissing: true,
                alwaysLinkToLastBuild: true,
                keepAll: true,
                reportDir: 'reports',
                reportFiles: 'report.html',
                reportName: 'Pytest HTML Report'
            ])
            allure includeProperties: false, jdk: '', results: [[path: 'reports/allure-results']]
            archiveArtifacts artifacts: 'reports/**', allowEmptyArchive: true
        }
        success {
            script {
                if (params.NOTIFY_EMAIL?.trim()) {
                    def htmlReportUrl = "${env.BUILD_URL}Pytest_20HTML_20Report/"
                    def allureReportUrl = "${env.BUILD_URL}allure/"
                    def totalCount = (env.TEST_TOTAL ?: '0') as Integer
                    def failCount = (env.TEST_FAIL ?: '0') as Integer
                    def skipCount = (env.TEST_SKIP ?: '0') as Integer
                    def passCount = (env.TEST_PASS ?: '0') as Integer
                    mail(
                        to: params.NOTIFY_EMAIL,
                        subject: "portfolio-automation build #${env.BUILD_NUMBER} execution passed",
                        mimeType: 'text/html',
                        body: """
                        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                            <div style="background-color: #f5f5f5; padding: 16px 20px; border-radius: 6px 6px 0 0;">
                                <h2 style="margin: 0; font-size: 20px; color: #2e7d32;">Build #${env.BUILD_NUMBER} Execution Passed</h2>
                            </div>
                            <div style="border: 1px solid #e0e0e0; border-top: none; padding: 20px; border-radius: 0 0 6px 6px;">
                                <table style="width: 100%; border-collapse: collapse; margin-bottom: 16px;">
                                    <tr>
                                        <td style="padding: 6px 0; color: #666; width: 140px;"><strong>Site tested</strong></td>
                                        <td style="padding: 6px 0;">${params.BASE_URL}</td>
                                    </tr>
                                    <tr>
                                        <td style="padding: 6px 0; color: #666;"><strong>Browser</strong></td>
                                        <td style="padding: 6px 0; text-transform: capitalize;">${params.BROWSER}</td>
                                    </tr>
                                    <tr>
                                        <td style="padding: 6px 0; color: #666;"><strong>Image</strong></td>
                                        <td style="padding: 6px 0;"><code>portfolio-automation:${env.BUILD_NUMBER}</code></td>
                                    </tr>
                                </table>
                                <div style="background-color: #f5f5f5; border-radius: 6px; padding: 14px 16px; margin-bottom: 20px;">
                                    <span style="color: #2e7d32; font-weight: bold;">${passCount} passed</span>
                                    &nbsp;&middot;&nbsp;
                                    <span style="color: #c62828; font-weight: bold;">${failCount} failed</span>
                                    &nbsp;&middot;&nbsp;
                                    <span style="color: #757575; font-weight: bold;">${skipCount} skipped</span>
                                    &nbsp;<span style="color: #999;">(${totalCount} total)</span>
                                </div>
                                <div style="margin-bottom: 8px;">
                                    <a href="${htmlReportUrl}" style="display: inline-block; background-color: #1565c0; color: #ffffff; text-decoration: none; padding: 10px 16px; border-radius: 4px; margin-right: 8px; font-size: 14px;">View Pytest Report</a>
                                    <a href="${allureReportUrl}" style="display: inline-block; background-color: #6a1b9a; color: #ffffff; text-decoration: none; padding: 10px 16px; border-radius: 4px; font-size: 14px;">View Allure Report</a>
                                </div>
                                <p style="margin-top: 20px; font-size: 13px; color: #999;">
                                    <a href="${env.BUILD_URL}" style="color: #999;">Full console output and build details</a>
                                </p>
                            </div>
                        </div>
                        """
                    )
                }
            }
        }
        failure {
            script {
                if (params.NOTIFY_EMAIL?.trim()) {
                    def htmlReportUrl = "${env.BUILD_URL}Pytest_20HTML_20Report/"
                    def allureReportUrl = "${env.BUILD_URL}allure/"
                    def totalCount = (env.TEST_TOTAL ?: '0') as Integer
                    def failCount = (env.TEST_FAIL ?: '0') as Integer
                    def skipCount = (env.TEST_SKIP ?: '0') as Integer
                    def passCount = (env.TEST_PASS ?: '0') as Integer
                    mail(
                        to: params.NOTIFY_EMAIL,
                        subject: "portfolio-automation build #${env.BUILD_NUMBER} execution failed",
                        mimeType: 'text/html',
                        body: """
                        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                            <div style="background-color: #f5f5f5; padding: 16px 20px; border-radius: 6px 6px 0 0;">
                                <h2 style="margin: 0; font-size: 20px; color: #c62828;">Build #${env.BUILD_NUMBER} Execution Failed</h2>
                            </div>
                            <div style="border: 1px solid #e0e0e0; border-top: none; padding: 20px; border-radius: 0 0 6px 6px;">
                                <table style="width: 100%; border-collapse: collapse; margin-bottom: 16px;">
                                    <tr>
                                        <td style="padding: 6px 0; color: #666; width: 140px;"><strong>Site tested</strong></td>
                                        <td style="padding: 6px 0;">${params.BASE_URL}</td>
                                    </tr>
                                    <tr>
                                        <td style="padding: 6px 0; color: #666;"><strong>Browser</strong></td>
                                        <td style="padding: 6px 0; text-transform: capitalize;">${params.BROWSER}</td>
                                    </tr>
                                </table>
                                <div style="background-color: #f5f5f5; border-radius: 6px; padding: 14px 16px; margin-bottom: 20px;">
                                    <span style="color: #2e7d32; font-weight: bold;">${passCount} passed</span>
                                    &nbsp;&middot;&nbsp;
                                    <span style="color: #c62828; font-weight: bold;">${failCount} failed</span>
                                    &nbsp;&middot;&nbsp;
                                    <span style="color: #757575; font-weight: bold;">${skipCount} skipped</span>
                                    &nbsp;<span style="color: #999;">(${totalCount} total)</span>
                                </div>
                                <div style="margin-bottom: 8px;">
                                    <a href="${env.BUILD_URL}console" style="display: inline-block; background-color: #c62828; color: #ffffff; text-decoration: none; padding: 10px 16px; border-radius: 4px; margin-right: 8px; font-size: 14px;">View Console Output</a>
                                    <a href="${htmlReportUrl}" style="display: inline-block; background-color: #1565c0; color: #ffffff; text-decoration: none; padding: 10px 16px; border-radius: 4px; margin-right: 8px; font-size: 14px;">Pytest Report</a>
                                    <a href="${allureReportUrl}" style="display: inline-block; background-color: #6a1b9a; color: #ffffff; text-decoration: none; padding: 10px 16px; border-radius: 4px; font-size: 14px;">Allure Report</a>
                                </div>
                            </div>
                        </div>
                        """
                    )
                }
            }
        }
    }
}