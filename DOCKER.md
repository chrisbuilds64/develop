# Docker Setup - ChrisBuilds64

Complete Docker setup with Backend API + PostgreSQL database.

## Quick Start

```bash
# Start everything
docker-compose up -d

# View logs
docker-compose logs -f backend

# Stop everything
docker-compose down

# Stop and remove volumes (fresh start)
docker-compose down -v
```

## Services

### Backend API
- **Container:** `chrisbuilds-backend`
- **Port:** 8000
- **URL:** http://localhost:8000
- **Health:** http://localhost:8000/health
- **Docs:** http://localhost:8000/docs

### PostgreSQL Database
- **Container:** `chrisbuilds-postgres`
- **Port:** 5432
- **Database:** chrisbuilds64
- **User:** chrisbuilds
- **Password:** dev_password_change_in_production

## Features

### Auto-Migrations
Migrations run automatically on container start via:
```bash
alembic upgrade head
```

### Hot Reload
Backend code is mounted as volume:
- Changes to Python files trigger auto-reload
- No rebuild needed during development

### Health Checks
Both containers have health checks:
- PostgreSQL: `pg_isready`
- Backend: HTTP health endpoint

## Development

### Run Commands in Container
```bash
# Shell access
docker exec -it chrisbuilds-backend sh

# Run Alembic commands
docker exec chrisbuilds-backend alembic revision -m "new migration"

# Database access
docker exec -it chrisbuilds-postgres psql -U chrisbuilds -d chrisbuilds64
```

### View Logs
```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f backend
docker-compose logs -f postgres
```

### Rebuild After Dependency Changes
```bash
# Rebuild images
docker-compose build

# Rebuild and start
docker-compose up -d --build
```

## Database

### Connect to PostgreSQL
```bash
# From host (if psql installed)
psql -h localhost -U chrisbuilds -d chrisbuilds64

# From container
docker exec -it chrisbuilds-postgres psql -U chrisbuilds -d chrisbuilds64
```

### Useful SQL Commands
```sql
-- List tables
\dt

-- Describe items table
\d items

-- Count items
SELECT COUNT(*) FROM items;

-- View all items (including soft-deleted)
SELECT id, label, deleted_at FROM items;
```

### Migrations
```bash
# Create new migration
docker exec chrisbuilds-backend alembic revision -m "description"

# Apply migrations
docker exec chrisbuilds-backend alembic upgrade head

# Rollback one migration
docker exec chrisbuilds-backend alembic downgrade -1

# View migration history
docker exec chrisbuilds-backend alembic history
```

## API Testing

### Health Check
```bash
curl http://localhost:8000/health
```

### Create Item
```bash
curl -X POST http://localhost:8000/api/v1/items \
  -H "Content-Type: application/json" \
  -d '{
    "label": "Test Item",
    "content_type": "text/note",
    "payload": {"text": "Hello from Docker!"},
    "tags": ["docker", "test"]
  }'
```

### List Items
```bash
# All items
curl http://localhost:8000/api/v1/items

# Filter by tag
curl http://localhost:8000/api/v1/items?tags=docker

# Filter by content type
curl http://localhost:8000/api/v1/items?content_type=text/note
```

### Get Item
```bash
curl http://localhost:8000/api/v1/items/{item_id}
```

### Update Item
```bash
curl -X PUT http://localhost:8000/api/v1/items/{item_id} \
  -H "Content-Type: application/json" \
  -d '{"label": "Updated Label"}'
```

### Delete Item (Soft Delete)
```bash
curl -X DELETE http://localhost:8000/api/v1/items/{item_id}
```

## Troubleshooting

### Container Won't Start
```bash
# Check logs
docker-compose logs backend
docker-compose logs postgres

# Restart services
docker-compose restart
```

### Database Connection Issues
```bash
# Check PostgreSQL is healthy
docker ps

# Verify database exists
docker exec chrisbuilds-postgres psql -U chrisbuilds -l
```

### Port Already in Use
```bash
# Check what's using port 8000 or 5432
lsof -i :8000
lsof -i :5432

# Stop conflicting process or change port in docker-compose.yml
```

### Fresh Start
```bash
# Stop everything and remove volumes
docker-compose down -v

# Remove all ChrisBuilds images
docker rmi develop-backend

# Start fresh
docker-compose up -d --build
```

## Production Notes

**Security:**
- Change PostgreSQL password in production
- Use environment variables for secrets
- Don't expose PostgreSQL port (5432) publicly
- Enable SSL/TLS for database connections

**Performance:**
- Remove volume mount (no hot reload needed)
- Use multi-stage build for smaller image
- Configure connection pooling
- Add reverse proxy (nginx/traefik)

**Monitoring:**
- Add logging aggregation
- Health check endpoints
- Metrics collection (Prometheus)
- Alert on container restarts
