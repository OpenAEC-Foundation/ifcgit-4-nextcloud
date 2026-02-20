#!/bin/bash
# Dev environment: databases in Docker, API + frontend locally
set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

case "${1:-start}" in
  start)
    echo -e "${GREEN}Starting databases...${NC}"
    docker compose -f docker-compose.dev.yml up -d
    echo -e "${GREEN}Waiting for PostgreSQL...${NC}"
    until docker compose -f docker-compose.dev.yml exec -T db pg_isready -U ifcgit 2>/dev/null; do sleep 1; done

    echo -e "${GREEN}Running migrations...${NC}"
    cd server
    DATABASE_URL="postgresql+asyncpg://ifcgit:ifcgit@localhost:5432/ifcgit" \
      python -m alembic upgrade head 2>/dev/null || echo -e "${YELLOW}Migrations skipped (run manually if needed)${NC}"
    cd ..

    echo -e "${GREEN}Starting API server...${NC}"
    cd server
    DATABASE_URL="postgresql+asyncpg://ifcgit:ifcgit@localhost:5432/ifcgit" \
    REDIS_URL="redis://localhost:6379/0" \
    SECRET_KEY="dev-secret-key" \
    DATA_DIR="$(pwd)/../data" \
    NEO4J_ENABLED=true \
    NEO4J_URI="bolt://localhost:7687" \
    uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload --log-level debug &
    API_PID=$!
    cd ..

    echo -e "${GREEN}Starting frontend...${NC}"
    cd frontend
    npx vite --port 3000 --open &
    FRONTEND_PID=$!
    cd ..

    echo ""
    echo -e "${GREEN}=== Dev environment ready ===${NC}"
    echo -e "  Frontend:  ${YELLOW}http://localhost:3000/app/${NC}"
    echo -e "  API:       ${YELLOW}http://localhost:8000/api/health${NC}"
    echo -e "  Neo4j:     ${YELLOW}http://localhost:7474${NC}"
    echo ""
    echo -e "  Press Ctrl+C to stop everything"
    echo ""

    trap "kill $API_PID $FRONTEND_PID 2>/dev/null; echo -e '\n${RED}Stopped.${NC}'" EXIT
    wait
    ;;

  stop)
    echo -e "${RED}Stopping databases...${NC}"
    docker compose -f docker-compose.dev.yml down
    pkill -f "uvicorn src.main:app" 2>/dev/null || true
    pkill -f "vite" 2>/dev/null || true
    echo -e "${GREEN}Done.${NC}"
    ;;

  db)
    echo -e "${GREEN}Starting only databases...${NC}"
    docker compose -f docker-compose.dev.yml up -d
    ;;

  logs)
    docker compose -f docker-compose.dev.yml logs -f
    ;;

  *)
    echo "Usage: ./dev.sh [start|stop|db|logs]"
    ;;
esac
