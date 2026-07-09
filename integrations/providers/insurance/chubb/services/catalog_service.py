from integrations.providers.insurance.chubb.api_client import ChubbApiClient
from integrations.providers.insurance.chubb import endpoints


class ChubbCatalogService:
    def __init__(self, client=None):
        self.client = client or ChubbApiClient()

    def health(self):
        return self.client.get(endpoints.HEALTH)

    def business_profiles(self, system_name=None):
        params = {}
        if system_name:
            params["SystemName"] = system_name
        return self.client.get(endpoints.BUSINESS_PROFILES, params=params)

    def agents(self, business_profile_name=None):
        params = {}
        if business_profile_name:
            params["BusinessProfileName"] = business_profile_name
        return self.client.get(endpoints.AGENTS, params=params)

    def groupings(self, business_profile_name=None, agent_id=None, agent_option_id=None):
        params = {}
        if business_profile_name:
            params["BusinessProfileName"] = business_profile_name
        if agent_id:
            params["AgentId"] = agent_id
        if agent_option_id:
            params["AgentOptionId"] = agent_option_id
        return self.client.get(endpoints.GROUPINGS, params=params)

    def rates(self, business_profile_name=None, grouping_id=None):
        params = {}
        if business_profile_name:
            params["BusinessProfileName"] = business_profile_name
        if grouping_id:
            params["GroupingId"] = grouping_id
        return self.client.get(endpoints.RATES, params=params)

    def vehicle_makes(self, business_profile_name, grouping_id, rate_id):
        params = {
            "BusinessProfileName": business_profile_name,
            "GroupingId": grouping_id,
            "RateId": rate_id,
        }
        return self.client.get(endpoints.VEHICLE_MAKES, params=params)
