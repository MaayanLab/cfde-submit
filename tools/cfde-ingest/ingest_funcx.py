
def ingest(userinfo=None, url=None, dcc_id=None, environment=None):
    try:

        import cfde_ingest.config
        import logging.config
        import uuid
        from cfde_ingest.ingest import IngestClient

        action_id = str(uuid.uuid1())
        cfde_ingest.config.logging["handlers"]["cloudwatch"]["log_stream_name"] = action_id
        logging.config.dictConfig(cfde_ingest.config.logging)
        client = IngestClient(userinfo=userinfo,
                              environment=environment,
                              dcc_id=dcc_id,
                              action_id=action_id)
        archive_url = client.move_to_protected_location(transfer_url=url)
        result = client.deriva_ingest(archive_url=archive_url)
        result["archive_url"] = archive_url
        result["submission_id"] = action_id
        return result

    except Exception:
        import traceback
        return {
            "success": False,
            "error": traceback.format_exc(),
            "review_browse_url": None,
            "archive_url": None,
            "submission_id": action_id
        }
