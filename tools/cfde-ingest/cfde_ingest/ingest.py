import cfde_ingest.config as config
import datetime
import globus_sdk
import logging
import os
import urllib.parse
import urllib.request
from cfde_deriva.registry import Registry, WebauthnUser, WebauthnAttribute
from cfde_deriva.submission import Submission
from globus_sdk import GlobusError
from deriva.core import DerivaServer, DEFAULT_SESSION_CONFIG


class IngestClient:
    def __init__(self, userinfo=None, environment=None, dcc_id=None, action_id=None):
        self.logger = logging.getLogger("cfde_ingest")
        self.action_id = action_id
        self.dcc_id = dcc_id
        self.userinfo = userinfo

        if environment not in config.environments:
            raise ValueError(f'Invalid environment {environment}')
        self.environment = environment

        try:
            self.webauthnuser = self.__webauthnuser_from_userinfo(userinfo)
        except (TypeError, KeyError):
            self.logger.exception("Error while parsing user info")
            raise

        self.logger.info(f"Initiated IngestClient: action_id={action_id}, "
                         f"user={userinfo['client']['display_name']}"
                         f"email={userinfo['client']['email']}, dcc={self.dcc_id}")

    @staticmethod
    def __webauthnuser_from_userinfo(userinfo):
        web_authn_user = WebauthnUser(
            userinfo['client']['id'],
            userinfo['client']['display_name'],
            userinfo['client'].get('full_name'),
            userinfo['client'].get('email'),
            [
                WebauthnAttribute(attr['id'], attr.get('display_name', 'unknown'))
                for attr in userinfo['attributes']
            ]
        )
        return web_authn_user

    def move_to_protected_location(self, transfer_url):
        """ Move user submitted datasets to a read-only location """
        action_id = self.action_id
        dcc_id = self.dcc_id
        transfer_token = self.__get_app_token(config.transfer_scope)
        auth = globus_sdk.AccessTokenAuthorizer(transfer_token)
        tc = globus_sdk.TransferClient(authorizer=auth)
        parsed_url = urllib.parse.urlparse(transfer_url)
        dcc_name = dcc_id.split(':')[1]
        dcc_dir = os.path.join(config.long_term_storage, dcc_name)
        old_ext = os.path.splitext(parsed_url.path)[1]
        new_filename = f"{datetime.datetime.now().isoformat()}-{action_id}{old_ext}"

        if not parsed_url.path.startswith(config.short_term_storage):
            raise ValueError("Transfer requested from non-staging directory: {transfer_url}")

        new_dataset_path = os.path.join(dcc_dir, new_filename)
        gcs_endpoint = getattr(config, self.environment)["gcs_endpoint"]

        try:
            tc.operation_rename(gcs_endpoint, parsed_url.path, new_dataset_path)
        except GlobusError:
            self.logger.exception(f"Failed to rename {parsed_url.path} to {new_dataset_path}")
            raise

        url = urllib.parse.urlunparse((parsed_url.scheme, parsed_url.netloc, new_dataset_path,
                                       "", "", ""))
        return url

    @staticmethod
    def __get_app_token(scope):
        cc_app = globus_sdk.ConfidentialAppAuthClient(
                    client_id=config.globus_cc_app,
                    client_secret=config.globus_secret)
        access_token = globus_sdk.ClientCredentialsAuthorizer(
                    scopes=scope,
                    confidential_client=cc_app)
        return access_token.access_token

    def deriva_ingest(self, archive_url):
        servername = getattr(config, self.environment)["server"]
        credential = {"bearer-token": self.__get_app_token(config.deriva_scope)}
        session_config = DEFAULT_SESSION_CONFIG.copy()
        session_config["allow_retry_on_all_methods"] = True
        registry = Registry('https', servername, credentials=credential, session_config=session_config)
        server = DerivaServer('https', servername, credential, session_config=session_config)
        submission_id = self.action_id
        registry.validate_dcc_id(self.dcc_id, self.webauthnuser)

        # The Header map protects from submitting our https_token to non-Globus URLs. This MUST
        # match, otherwise the Submission() client will attempt to download the Globus GCS Auth
        # login page instead. r"https://[^/]*[.]data[.]globus[.]org/.*" will match most GCS HTTP
        # pages, but if a custom domain is used this MUST be updated to use that instead.
        globus_ep = getattr(config, self.environment)["gcs_endpoint"]
        https_token = self.__get_app_token(f'https://auth.globus.org/scopes/{globus_ep}/https')
        header_map = {
            config.allowed_gcs_https_hosts: {"Authorization": f"Bearer {https_token}"}
        }

        submission = Submission(server, registry, submission_id, self.dcc_id, archive_url,
                                self.webauthnuser, archive_headers_map=header_map)
        submission.ingest()

        md = registry.get_datapackage(submission_id)
        success = md["status"] == 'cfde_registry_dp_status:content-ready'
        error = md.get('diagnostics')
        result = {"success": success,
                  "error": error,
                  "review_browse_url": md["review_browse_url"]}
        return result
