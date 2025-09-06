p/ipeline {
    agent any

    environment {
        COMPOSE_FILE = 'docker-compose.yml'
    }

    stages {
        stage('Checkout') {
            steps {
                checkout scm
            }
        }

        stage('Build') {
            steps {
                script {
                    echo 'Building Docker images...'
                    sh 'docker-compose build --pull --no-cache'
                }
            }
        }

        stage('Test') {
            steps {
                script {
                    echo 'Running basic smoke test...'
                    // Try to run a simple command inside the built api container
                    sh '''
                      docker-compose up -d db || true
                      docker-compose run --rm api python -c "import sys; print('python-run-ok'); sys.exit(0)"
                    '''
                }
            }
        }

        stage('Deploy') {
            steps {
                script {
                    echo 'Bringing stack up...'
                    sh 'docker-compose up -d'
                }
            }
        }
    }

    post {
        always {
            script {
                echo 'Post: cleanup dangling resources...'
                sh 'docker system prune -f || true'
            }
        }
    }
}
