pipeline {
    agent any

    stages {
        stage('Checkout') {
            steps {
                git branch: 'main', url: 'https://github.com/TheBishop97/Linux1.git', credentialsId: '73ff62e5-d264-42a1-8514-ba7c89303545'
            }
        }

        stage('Build') {
            steps {
                echo 'Building Docker images...'
                sh '''
                    # Copy .env if missing
                    if [ ! -f .env ]; then
                        cp .env.example .env
                    fi
		# Clean up existing containers to avoid name conflicts
                    docker-compose down --remove-orphans || true

                    docker-compose build --pull --no-cache
                '''
            }
        }

        stage('Run') {
            steps {
                echo 'Starting containers...'
                sh '''
                    docker-compose up -d
                '''
            }
        }

        stage('Test') {
            steps {
                echo 'Testing API...'
                sh '''
                    # Optional: add simple healthcheck
                    curl -f http://localhost:8000 || exit 1
                '''
            }
        }

        stage('Cleanup') {
            steps {
                echo 'Cleaning dangling resources...'
                sh '''
                    docker system prune -f
                '''
            }
        }
    }
}
