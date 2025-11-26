from app.core.config import settings
import app.db.test_connection


print(settings.DATABASE_URI)
print(settings.SECRET_KEY)
print(settings.CORS_ORIGINS)

app.db.test_connection.test()