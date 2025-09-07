pipeline {
    agent any

    stages {
        stage('Checkout') {
            steps {
                checkout scm
            }
        }

        stage('Prepare Env') {
            steps {
                echo 'Preparing environment file...'
                sh '''
                if [ ! -f .env ]; then
                  cp .env.example .env
                  echo ".env file created from .env.example"
                else
                  echo ".env file already exists"
                fi
                '''
            }
        }

        stage('Build') {
            steps {
                echo 'Building Docker images...'
                sh 'docker-compose build --pull --no-cache'
            }
        }

        stage('Test') {
            steps {
                echo 'Running tests...'
                // Add your test commands here
                sh 'docker-compose run --rm app pytest || true'
            }
        }

        stage('Deploy') {
            steps {
                echo 'Deploying containers...'
                sh 'docker-compose up -d'
            }
        }
    }

    post {
        always {
            echo 'Post: cleanup dangling resources...'
            sh 'docker system prune -f || true'
        }
    }
}
