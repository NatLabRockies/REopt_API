# REopt®, Copyright (c) Alliance for Sustainable Energy, LLC. See also https://github.com/NatLabRockies/REopt_API/blob/master/LICENSE.
from django.db import models
import uuid
import os
import datetime, tzlocal
from reo.models import ScenarioModel
import logging
from proforma.proforma_generator import generate_proforma
log = logging.getLogger(__name__)


class ProForma(models.Model):

    scenariomodel = models.OneToOneField(
        ScenarioModel,
        on_delete=models.CASCADE,
        default=0,
        to_field='id',
        blank=True,
        primary_key=True
    )
    uuid = models.UUIDField(default=uuid.uuid4, null=False)
    spreadsheet_created = models.DateTimeField(null=True)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    
    @classmethod
    def create(cls, scenariomodel, **kwargs ):
        pf = cls(scenariomodel = scenariomodel, **kwargs)
        file_dir = os.path.dirname(pf.output_file)
        if not os.path.exists(file_dir):
            os.mkdir(file_dir)
        pf.save()        
        return pf
    
    @property
    def sheet_io(self):
        return "Inputs and Outputs"

    @property
    def output_file_name(self):
        return "ProForma.xlsm"

    @property
    def output_file(self):
        folder = os.path.join(os.getcwd(),'static', 'files', str(self.uuid))
        if not os.path.exists(folder):
            os.makedirs(folder)
        return os.path.join(folder, self.output_file_name)
          
    def generate_spreadsheet(self):
        log.info("Generating proforma spreadsheet")
        generate_proforma(self.scenariomodel, self.output_file)
        self.spreadsheet_created = tzlocal.get_localzone().localize(datetime.datetime.now())
        return True
