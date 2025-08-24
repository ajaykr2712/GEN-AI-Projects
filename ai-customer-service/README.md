# AI Customer Service Assistant

A comprehensive AI-powered customer service system capable of handling real-time customer inquiries, processing logs, and providing intelligent assistance.

## Features

- **Real-time AI Chat**: Intelligent responses using advanced language models
- **Log Processing**: Fetch and analyze timestamped customer inquiry logs
- **FAQ System**: Automated handling of frequently asked questions
- **Troubleshooting Assistant**: Guided problem resolution
- **Multi-user Support**: Handle multiple concurrent conversations
- **Secure Authentication**: JWT-based user authentication
- **Scalable Architecture**: Docker-ready deployment
- **Analytics Dashboard**: Monitor system performance and user interactions

## Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Frontend      │    │   Backend API   │    │   AI Engine     │
│   (React)       │◄──►│   (FastAPI)     │◄──►│   (OpenAI)      │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                              │
                              ▼
                    ┌─────────────────┐    ┌─────────────────┐
                    │   Database      │    │   Log Processor │
                    │   (PostgreSQL)  │    │   (Async)       │
                    └─────────────────┘    └─────────────────┘
```

## Quick Start

### Prerequisites
- Python 3.8+
- Node.js 16+
- Docker (optional)

### Backend Setup
```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload
```

### Frontend Setup
```bash
cd frontend
npm install
npm start
```

### Docker Deployment
```bash
docker-compose up -d
```

## Configuration

1. Copy `.env.example` to `.env`
2. Set your OpenAI API key and other configuration variables
3. Run database migrations

## API Documentation

Once running, visit `http://localhost:8000/docs` for interactive API documentation.

## License

MIT License
