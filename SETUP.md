# Setup Guide for Tekk.coach Security Analyzer

## Prerequisites

- Python 3.8 or higher
- OpenAI API key
- Git (for repository analysis)

## Installation

1. **Clone and install dependencies:**
   ```bash
   git clone <repository-url>
   cd tekk3-python
   pip install -r requirements.txt
   ```

2. **Set up environment variables:**
   ```bash
   cp .env.example .env
   # Edit .env and add your OpenAI API key
   ```

3. **Configure your OpenAI API key:**
   ```bash
   # Edit .env file
   OPENAI_API_KEY=your_actual_openai_api_key_here
   OPENAI_MODEL=gpt-4
   OPENAI_TEMPERATURE=0.1
   ```

## Usage

### Basic Usage
```bash
python agent.py --repo /path/to/repo --stack "Next.js + Express"
```

### With Output Files
```bash
python agent.py --repo /path/to/repo \
  --stack "React + Node.js" \
  --output security-report.json \
  --tickets jira-tickets.json
```

### Test with a GitHub Repository
```bash
# Clone a repository first
git clone https://github.com/username/repository.git
cd repository

# Run analysis
python /path/to/tekksec/agent.py --repo . --stack "Your Tech Stack"
```

## Environment Variables

- `OPENAI_API_KEY`: Your OpenAI API key (required)
- `OPENAI_MODEL`: Model to use (default: gpt-4)
- `OPENAI_TEMPERATURE`: Temperature for responses (default: 0.1)

## Troubleshooting

1. **"OPENAI_API_KEY environment variable is required"**
   - Make sure you've set up your .env file with a valid OpenAI API key

2. **"Path is not a git repository"**
   - The repository must be a git repository for analysis

3. **JSON parsing errors**
   - The system will fall back to a minimal report if the LLM response is malformed

## Example GitHub Repositories to Test

Here are some good repositories to test with:

- **Simple Node.js app**: `https://github.com/expressjs/express`
- **React application**: `https://github.com/facebook/react`
- **Python Flask app**: `https://github.com/pallets/flask`
- **Full-stack app**: `https://github.com/vercel/next.js`

## Getting Your OpenAI API Key

1. Go to [OpenAI Platform](https://platform.openai.com/)
2. Sign up or log in
3. Go to API Keys section
4. Create a new API key
5. Copy the key and add it to your .env file
