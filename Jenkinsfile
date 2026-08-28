// Jenkins Pipeline for the portfolio website automation suite.
// Stages now mirror the confirmed architecture more closely:
//   Jenkins master splits into two parallel jobs -
//     Deployment Job  -> builds the Docker image
//     Execution Job   -> calls the "execution API" to construct the
//                         actual test command from parameters
//   Both converge at Run Tests, which uses what Execution Job produced.
//
// Prerequisites on the Jenkins server itself:
//   - Docker installed, and the Jenkins user able to run `docker` commands
//   - "HTML Publisher" plugin installed
//   - This Jenkinsfile checked into the repo Jenkins is pointed at

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
    }

    environment {
        IMAGE_NAME = 'portfolio-automation'
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
                        echo 'Deployment job: building Docker image with the checked-out code.'
                        sh 'docker build --no-cache -t ${IMAGE_NAME} .'
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
                // Both parallel branches have finished here: the image
                // exists (Deployment Job) and docker_run_args.txt holds
                // whatever the Execution Job's API decided to run.
                sh '''
                    mkdir -p reports
                    DOCKER_RUN_ARGS=$(cat docker_run_args.txt)
                    echo "Running with args: '${DOCKER_RUN_ARGS}'"
                    docker run --rm \
                        -e BASE_URL="${BASE_URL}" \
                        -v "${WORKSPACE}/reports:/app/reports" \
                        ${IMAGE_NAME} ${DOCKER_RUN_ARGS}
                '''
            }
        }
    }

    post {
        always {
            publishHTML(target: [
                allowMissing: true,
                alwaysLinkToLastBuild: true,
                keepAll: true,
                reportDir: 'reports',
                reportFiles: 'report.html',
                reportName: 'Pytest HTML Report'
            ])
            archiveArtifacts artifacts: 'reports/**', allowEmptyArchive: true
        }
    }
}