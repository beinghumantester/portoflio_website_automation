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
            defaultValue: '',
            description: 'Email address for build result notifications. Leave blank to skip.'
        )
    }

    environment {
        IMAGE_NAME = 'portfolio-automation'
        IMAGE_TAG = "${env.BUILD_NUMBER}"
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

                    docker compose up -d selenium-hub chrome-node firefox-node
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
            junit testResults: 'reports/junit.xml', allowEmptyResults: true
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
                    def testAction = currentBuild.testResultAction
                    def totalCount = testAction ? testAction.totalCount : 0
                    def failCount = testAction ? testAction.failCount : 0
                    def skipCount = testAction ? testAction.skipCount : 0
                    def passCount = totalCount - failCount - skipCount
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
                    def testAction = currentBuild.testResultAction
                    def totalCount = testAction ? testAction.totalCount : 0
                    def failCount = testAction ? testAction.failCount : 0
                    def skipCount = testAction ? testAction.skipCount : 0
                    def passCount = totalCount - failCount - skipCount
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