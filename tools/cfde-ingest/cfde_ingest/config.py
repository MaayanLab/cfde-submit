deriva_scope = "https://auth.globus.org/scopes/app.nih-cfde.org/deriva_all"
environments = ["dev", "staging", "prod"]
globus_cc_app = "KEY_HERE"
globus_secret = "SECRET_HERE"
long_term_storage = "/CFDE/public/"
short_term_storage = "/CFDE/data/"
transfer_scope = "urn:globus:auth:scope:transfer.api.globus.org:all"
allowed_gcs_https_hosts = r"https://[^/]*[.]data[.]globus[.]org/.*"

dev = {
    "server": "app-dev.nih-cfde.org",
    "gcs_endpoint": "36530efa-a1e3-45dc-a6e7-9560a8e9ac49",
}
staging = {
    "server": "app-staging.nih-cfde.org",
    "gcs_endpoint": "922ee14d-49b7-4d69-8f1c-8e2ff8207542"
}
prod = {
    "server": "app.nih-cfde.org",
    "gcs_endpoint": "d4c89edc-a22c-4bc3-bfa2-bca5fd19b404",
}

logging = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "basic": {
            "format": "[{asctime}] [{levelname}] {name}: {message}",
            "style": "{",
            "datefmt": "%Y-%m-%d %H:%M:%S",
        },
        "cloudwatch": {
            "format": "[{levelname}] {name}: {message}",
            "style": "{",
        }
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "level": "DEBUG",
            "formatter": "basic",
        },
        "cloudwatch": {
            "class": "watchtower.CloudWatchLogHandler",
            "level": "DEBUG",
            "formatter": "cloudwatch",
            "log_group_name": "cfde-ingest",
            "log_stream_name": "{strftime:%Y-%m-%d}",
            "send_interval": 10,
        }
    },
    "loggers": {
        "cfde_ingest": {
            "level": "INFO",
            "handlers": ["console", "cloudwatch"],
            "propagate": False,
        },
        "cfde_deriva": {
            "level": "INFO",
            "handlers": ["console", "cloudwatch"],
            "propagate": False,
        },
        "bdbag": {
            "level": "WARNING",
            "handlers": ["console", "cloudwatch"],
            "propagate": False,
        },
        "globus_sdk": {
            "level": "WARNING",
            "handlers": ["console", "cloudwatch"],
            "propagate": False,
        },
    },
}
