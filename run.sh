#!/bin/bash
# run.sh - Production startup script with proper cleanup

echo "🚀 Starting Product Comparison Hub..."

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is required but not installed. Please install Python 3.8 or higher."
    exit 1
fi

# Check if pip is installed
if ! command -v pip3 &> /dev/null; then
    echo "❌ pip3 is required but not installed. Please install pip3."
    exit 1
fi

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install dependencies
echo "📥 Installing dependencies..."
pip install -r requirements.txt

# Create data directory if it doesn't exist
mkdir -p data

# Set production environment variables
export FLASK_ENV=production
export FLASK_DEBUG=false

# Function to cleanup processes on exit
cleanup() {
    echo ""
    echo "🛑 Shutting down Product Comparison Hub..."
    if [ ! -z "$FLASK_PID" ]; then
        kill $FLASK_PID 2>/dev/null
        wait $FLASK_PID 2>/dev/null
    fi
    # Kill any remaining python processes running the app
    pkill -f "python.*app.py" 2>/dev/null || true
    echo "✅ Server stopped successfully."
    exit 0
}

# Set up signal handlers for cleanup
trap cleanup SIGINT SIGTERM EXIT

# Start the application
echo "🌟 Starting the application on http://localhost:5007"
echo "⏹️  Press Ctrl+C to stop the application"

# Start Python application in background and capture PID
python3 app.py &
FLASK_PID=$!

# Wait for the background process
wait $FLASK_PID
