# REopt®, Copyright (c) Alliance for Sustainable Energy, LLC. See also https://github.com/NatLabRockies/REopt_API/blob/master/LICENSE.
from django.db import models
import copy
import pandas as pd
from reo.models import ScenarioModel

year = 2021
"""
The year is used to instantiate the future costs object with the appropriate cost forecasts.
Note that there is only data for 2021 currently.
"""


class BaseModel(object):

    @property
    def dict(self):
        """
        Serialize Django Model.__dict__
        NOTE: to get correct field types you must run self.clean_fields() first (eg. convert int to float)
        :return: dict
        """
        d = copy.deepcopy(self.__dict__)
        d.pop("_state", None)
        d.pop("id", None)
        d.pop("basemodel_ptr_id", None)
        d.pop("run_uuid", None)  # redundant with base_scenario
        return d

    @classmethod
    def create(cls, **kwargs):
        obj = cls(**kwargs)
        return obj


class FutureCostsJob(BaseModel, models.Model):
    name = "FutureCostsJob"
    future_scenarios = [
        "future_scenario{}".format(i) for i in range(1,11)
    ]

    run_uuid = models.UUIDField(unique=True)
    description = models.TextField(blank=True)
    status = models.TextField(blank=True)
    created = models.DateTimeField(auto_now_add=True)

    # TODO: allow user provided future costs?

    base_scenario = models.OneToOneField(
        ScenarioModel,
        to_field='run_uuid',
        on_delete=models.CASCADE,
    )
    base_year = models.IntegerField()

    future_scenario1 = models.OneToOneField(
        ScenarioModel,
        related_name="future_scenario1",
        to_field='run_uuid',
        on_delete=models.CASCADE,
        blank=True,
        null=True
    )
    future_year1 = models.IntegerField(
        blank=True,
        null=True
    )

    future_scenario2 = models.OneToOneField(
        ScenarioModel,
        related_name="future_scenario2",
        to_field='run_uuid',
        on_delete=models.CASCADE,
        blank=True,
        null=True
    )
    future_year2 = models.IntegerField(
        blank=True,
        null=True
    )

    future_scenario3 = models.OneToOneField(
        ScenarioModel,
        related_name="future_scenario3",
        to_field='run_uuid',
        on_delete=models.CASCADE,
        blank=True,
        null=True
    )
    future_year3 = models.IntegerField(
        blank=True,
        null=True
    )

    future_scenario4 = models.OneToOneField(
        ScenarioModel,
        related_name="future_scenario4",
        to_field='run_uuid',
        on_delete=models.CASCADE,
        blank=True,
        null=True
    )
    future_year4 = models.IntegerField(
        blank=True,
        null=True
    )

    future_scenario5 = models.OneToOneField(
        ScenarioModel,
        related_name="future_scenario5",
        to_field='run_uuid',
        on_delete=models.CASCADE,
        blank=True,
        null=True
    )
    future_year5 = models.IntegerField(
        blank=True,
        null=True
    )

    future_scenario6 = models.OneToOneField(
        ScenarioModel,
        related_name="future_scenario6",
        to_field='run_uuid',
        on_delete=models.CASCADE,
        blank=True,
        null=True
    )
    future_year6 = models.IntegerField(
        blank=True,
        null=True
    )

    future_scenario7 = models.OneToOneField(
        ScenarioModel,
        related_name="future_scenario7",
        to_field='run_uuid',
        on_delete=models.CASCADE,
        blank=True,
        null=True
    )
    future_year7 = models.IntegerField(
        blank=True,
        null=True
    )

    future_scenario8 = models.OneToOneField(
        ScenarioModel,
        related_name="future_scenario8",
        to_field='run_uuid',
        on_delete=models.CASCADE,
        blank=True,
        null=True
    )
    future_year8 = models.IntegerField(
        blank=True,
        null=True
    )

    future_scenario9 = models.OneToOneField(
        ScenarioModel,
        related_name="future_scenario9",
        to_field='run_uuid',
        on_delete=models.CASCADE,
        blank=True,
        null=True
    )
    future_year9 = models.IntegerField(
        blank=True,
        null=True
    )

    future_scenario10 = models.OneToOneField(
        ScenarioModel,
        related_name="future_scenario10",
        to_field='run_uuid',
        on_delete=models.CASCADE,
        blank=True,
        null=True
    )
    future_year10 = models.IntegerField(
        blank=True,
        null=True
    )

    def clean(self):
        if not self.base_year:
            self.base_year = int(self.base_scenario.created.year)

    def update_status(self):
        statuses = []
        for fs in self.future_scenarios:
            try:
                statuses.append(
                    eval("self.{}.status".format(fs))
                )
            except:
                statuses.append("error")
        if any([s == "Optimizing..." for s in statuses]):
            self.status = "Optimizing..."
        elif all([s == "optimal" for s in statuses]):
            self.status = "optimal"
        elif any(["error" in s for s in statuses]):
            self.status = ("At least one scenario has an error. "
                           "Please check the individual results for more information.")


class CostForecasts(object):

    reopt_size_class_to_dGen_hub_height = {
        'residential': 20,
        'commercial': 40,
        'medium': 50,
        'large': 80,
    }

    def __init__(self, year: int):
        self.base_year = year
        self.wind_costs = pd.read_csv("futurecosts/cost_data/{}/wind_prices.csv".format(year))
        self.pv_costs = pd.read_csv("futurecosts/cost_data/{}/ATB_2021_PV_costs.csv".format(year))
        self.pv_costs.index = self.pv_costs.type
        self.pv_costs.drop("type", axis=1, inplace=True)
        self.pv_costs.columns = self.pv_costs.columns.astype(int)

    def wind(self, year: int, type: str, size_class: str) -> float:
        """
        Return capital or O&M costs for given year. See README.md for more.
        :param year: any int from 2022 to 2050 inclusive
        :param type: one of ["capital_cost_dollars_per_kw", "fixed_om_dollars_per_kw_per_yr"]
        :param size_class: one of  ['residential', 'commercial', 'medium', 'large']
        :return: future cost
        """
        height = self.reopt_size_class_to_dGen_hub_height[size_class]
        filtered_wind_costs = self.wind_costs[self.wind_costs.default_tower_height_m == height]
        filtered_wind_costs.index = filtered_wind_costs.year
        filtered_wind_costs = filtered_wind_costs[type].copy()

        if year in filtered_wind_costs.index:
            return filtered_wind_costs.loc[year]

        filtered_wind_costs.loc[year] = None
        filtered_wind_costs.sort_index(inplace=True)
        filtered_wind_costs = filtered_wind_costs.astype(float).interpolate(axis=0)

        return round(filtered_wind_costs.loc[year], 2)

    def pv(self, year: int, type: str) -> int:
        """
        Return capital or O&M costs from NLR ATB forecasts for given year.
        As of 2021-03-30 we have values for each year from 2022 to 2050 inclusive
        :param year: any int from 2022 to 2050 inclusive
        :param type: one of ["capital_cost_dollars_per_kw", "fixed_om_dollars_per_kw_per_yr"]
        :return: float, cost taken from NLR ATB
        """
        return self.pv_costs.loc[type, year]

    def storage(self, year: int, type: str) -> float:
        """
        Return capital costs for given year. See README.md for more.
        :param year: any int from 2022 to 2050 inclusive
        :param type: one of ["installed_cost_us_dollars_per_kw", "installed_cost_us_dollars_per_kwh"]
        return: future cost
        """
        annual_cost_reduction = 0.055
        base_kw_cost = 840.0
        base_kwh_cost = 420.0
        years = year - self.base_year
        if type == "installed_cost_us_dollars_per_kw":
            return base_kw_cost * (1-annual_cost_reduction)**years
        elif type == "installed_cost_us_dollars_per_kwh":
            return base_kwh_cost * (1-annual_cost_reduction)**years
        else:
            raise NotImplementedError("""
                type must be one of ["installed_cost_us_dollars_per_kw", "installed_cost_us_dollars_per_kwh"]
            """)


cost_forecasts = CostForecasts(year=year)
