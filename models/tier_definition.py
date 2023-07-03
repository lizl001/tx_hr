# Copyright 2019 Open Source Integrators
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, models


class TierDefinition(models.Model):
    _inherit = "tier.definition"

    @api.model
    def _get_tier_validation_model_names(self):
        res = super()._get_tier_validation_model_names()
        res_list = ["tx.hr.overtime", "tx.hr.withhold", "tx.hr.piece.rate", "tx.hr.other.subsidies", "tx.hr.leave",
                    "tx.hr.performance.coefficient", "tx.hr.business.trip", "tx.hr.depart",
                    "tx.hr.card.replacement.application","tx.hr.apply.full.member"]
        res += res_list
        return res
