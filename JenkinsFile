// Jenkins Pipeline for the portfolio website automation suite.
// Stages map to the confirmed architecture: Docker build -> Docker run
// (Pytest + Selenium) -> reports published as a Jenkins artifact.
//
// Prerequisites on the Jenkins server itself:
//   - Docker installed, and the Jenkins user able to run `docker` commands
//     (on Linux: `sudo usermod -aG docker jenkins`, then restart Jenkins -
//     same permission issue you hit locally with your own user applies to
//     the jenkins service account too)
//   - "HTML Publisher" plugin installed, so the Publish Report stage works
//   - This Jenkinsfile checked into the repo Jenkins is pointed at

pipeline {
    agent any

    parameters {
        string(
            name: 'BASE_URL',
            defaultValue: 'https://beinghumantester.com',
            description: 'URL of the portfolio site to test against'
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

        stage('Build Docker Image') {
            steps {
                sh 'docker build --no-cache -t ${IMAGE_NAME} .'
            }
        }

        stage('Run Tests') {
            steps {
                // Reports land in a workspace-local folder via the volume
                // mount, so Jenkins can pick them up as artifacts after
                // the container exits - same principle as the confirmed
                // pipeline's "volume mount -> persistent location" step,
                // just landing in the Jenkins workspace instead of a
                // separate Azure location for now.
                sh '''
                    mkdir -p reports
                    docker run --rm \
                        -e BASE_URL="${BASE_URL}" \
                        -v "${WORKSPACE}/reports:/app/reports" \
                        ${IMAGE_NAME}
                '''
            }
        }
    }

    post {
        always {
            // Publishes reports/report.html as a viewable report on the
            // Jenkins build page itself - requires the HTML Publisher plugin.
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