class Config:
    """Base configuration."""
    SQLALCHEMY_DATABASE_URI = 'sqlite:///default.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    # Common configurations that are shared across all environments

class ProductionConfig(Config):
    """Production configuration."""
    SQLALCHEMY_DATABASE_URI = 'sqlite:///prod.db'