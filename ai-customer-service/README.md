# AI Customer Service Assistant

<<<<<<< HEAD
A comprehensive AI-powered customer service system built with FastAPI, React, and OpenAI integration.

## 🚀 Quick Start

### Using Docker (Recommended)

```bash
# Clone the repository
git clone <your-repo-url>
cd ai-customer-service

# Start all services
docker-compose up -d

# Access the application
# Frontend: http://localhost:3000
# Backend API: http://localhost:8000
# API Docs: http://localhost:8000/docs
```

### Local Development

```bash
# Backend setup
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload

# Frontend setup (in another terminal)
=======
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
>>>>>>> 558fee2 (Add README.md for AI Customer Service Assistant project)
cd frontend
npm install
npm start
```

<<<<<<< HEAD
## 📁 Project Structure

```
ai-customer-service/
├── backend/                 # FastAPI backend
│   ├── app/                 # Application code
│   ├── tests/               # Backend tests
│   ├── main.py              # Entry point
│   └── requirements.txt     # Python dependencies
├── frontend/                # React frontend
│   ├── src/                 # Source code
│   ├── public/              # Static assets
│   └── package.json         # Node dependencies
├── .github/workflows/       # CI/CD pipelines
├── docker-compose.yml       # Docker orchestration
└── README.md               # This file
```

## 🔧 Configuration

### Environment Variables

Create `backend/.env`:

```env
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/ai_customer_service
SECRET_KEY=your-secret-key-here
OPENAI_API_KEY=your-openai-api-key
REDIS_URL=redis://localhost:6379
```

## 🧪 Testing

```bash
# Backend tests
cd backend
python -m pytest tests/ -v

# Frontend tests
cd frontend
npm test

# Run workflow validation
./validate-workflow.sh
```

## 📚 Documentation

- [API Documentation](API.md) - Complete API reference
- [Deployment Guide](DEPLOYMENT.md) - Production deployment instructions

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests: `./validate-workflow.sh`
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License.

## 🆘 Support

For issues and questions:
- Check the [DEPLOYMENT.md](DEPLOYMENT.md) for common troubleshooting
- Review the API documentation in [API.md](API.md)
- Run `./validate-workflow.sh` to check for configuration issues
=======
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
>>>>>>> 558fee2 (Add README.md for AI Customer Service Assistant project)
