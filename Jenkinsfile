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
                    mail(
                        to: params.NOTIFY_EMAIL,
                        subject: "SUCCESS: portfolio-automation build #${env.BUILD_NUMBER}",
                        body: """Build #${env.BUILD_NUMBER} passed.

BASE_URL: ${params.BASE_URL}
BROWSER: ${params.BROWSER}
Image: portfolio-automation:${env.BUILD_NUMBER}

Full report: ${env.BUILD_URL}
"""
                    )
                }
            }
        }
        failure {
            script {
                if (params.NOTIFY_EMAIL?.trim()) {
                    mail(
                        to: params.NOTIFY_EMAIL,
                        subject: "FAILED: portfolio-automation build #${env.BUILD_NUMBER}",
                        body: """Build #${env.BUILD_NUMBER} failed.

BASE_URL: ${params.BASE_URL}
BROWSER: ${params.BROWSER}

Check console output and the HTML/Allure reports for details: ${env.BUILD_URL}
"""
                    )
                }
            }
        }
    }
}