#!/bin/bash

echo "🚀 Starting Document Analysis Chatbot System..."

# Check if docker-compose is available
if ! command -v docker-compose &> /dev/null; then
    echo "❌ docker-compose is not installed. Please install docker-compose first."
    exit 1
fi

# Start infrastructure services
echo "📦 Starting infrastructure services (PostgreSQL, Redis, ChromaDB)..."
docker-compose up -d postgres redis chromadb

# Wait for services to be ready
echo "⏳ Waiting for services to start..."
sleep 10

# Check if services are running
echo "🔍 Checking service health..."
if ! docker-compose ps | grep -q "Up"; then
    echo "❌ Some services failed to start. Please check docker-compose logs."
    exit 1
fi

echo "✅ Infrastructure services are ready!"

# Start FastAPI backend
echo "🔧 Starting FastAPI backend..."
cd backend
python -m uvicorn main:app --host 0.0.0.0 --port 8001 --reload &
BACKEND_PID=$!
cd ..

# Wait for backend to start
echo "⏳ Waiting for backend to start..."
sleep 5

# Check if backend is responding
if ! curl -s http://localhost:8001/health > /dev/null; then
    echo "❌ Backend failed to start. Please check the logs."
    kill $BACKEND_PID 2>/dev/null
    exit 1
fi

echo "✅ Backend is ready!"

# Start Streamlit frontend
echo "🖥️ Starting Streamlit frontend..."
cd frontend
streamlit run main.py --server.port 8501 --server.address 0.0.0.0 &
FRONTEND_PID=$!
cd ..

echo "✅ All services started successfully!"
echo ""
echo "🌐 Access the application:"
echo "   Frontend (Streamlit): http://localhost:8501"
echo "   Backend API: http://localhost:8001"
echo "   API Documentation: http://localhost:8001/docs"
echo ""
echo "📊 Service URLs:"
echo "   ChromaDB: http://localhost:8000"
echo "   PostgreSQL: localhost:5432"
echo "   Redis: localhost:6379"
echo ""
echo "⚠️  Note: Make sure to configure your GPT-OSS API settings in .env file"
echo ""
echo "Press Ctrl+C to stop all services"

# Wait for interrupt
trap 'echo "🛑 Stopping services..."; kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; docker-compose down; exit 0' INT
wait