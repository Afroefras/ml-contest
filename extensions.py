from flask_limiter import Limiter
from flask_wtf.csrf import CSRFProtect
from flask_sqlalchemy import SQLAlchemy
from flask_limiter.util import get_remote_address

# Instancias “sin app”
db    = SQLAlchemy()
csrf  = CSRFProtect()

# Limitar el tráfico de una misma IP
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["50 per day", "10 per hour", "20 per minute"]
)
