from datetime import datetime
from odoo.exceptions import ValidationError
from odoo import fields, models, api
import re


class TxHrDepart(models.Model):
    _name = "tx.hr.depart"
    _inherit = 'tier.validation'
    _description = "辞职申请单"

    _tier_validation_manual_config = False

    pin = fields.Char(string='工号', readonly=True, related='employee_id.pin', store=True)
    employee_id = fields.Many2one('hr.employee', string='申请人', required=True, readonly=True)
    department_id = fields.Many2one('hr.department', string='部门', related='employee_id.department_id', readonly=True)
    job_id = fields.Many2one('hr.job', string='职务', related='employee_id.job_id', readonly=True)
    # date_hired = fields.Date('入职时间', related='employee_id.first_contract_date', readonly=True)
    application_date = fields.Date(string="申请日期", default=datetime.now())
    pre_resignation_date = fields.Date(string="预辞职日期", default=datetime.now())
    employee_ids = fields.Many2many('hr.employee', string='员工', required=True)
    resignation_type = fields.Selection([
        ('resign', '辞职'),
        ('dismiss', '辞退'),
        ('dissuade', '劝退'),
        ('expel', '开除')
    ], string='辞职类型', widget='radio')
    reason = fields.Text(string='辞职原因')
    opinion_direct_manager = fields.Text(string='直属负责人意见')
    opinion_factory = fields.Text(string='厂长意见')
    opinion_supervisor = fields.Text(string='人事主管意见')
    opinion_manager = fields.Text(string='总经理意见')
    department_handle_thing = fields.Char(string='本部门办理事项')
    factory_handle_thing = fields.Char(string='厂部办理事项')
    attachment_ids = fields.Many2many('ir.attachment', string='附件上传', limit=3)
    state = fields.Selection([
        ('draft', '草稿'),
        ('pending', '申请中'),
        ('approved', '审批通过'),
        ('rejected', '已拒绝')
    ], string='State', default='draft')
    depart_state = fields.Selection([
        ('draft', '草稿'),
        ('pending', '申请中'),
        ('approved', '审批通过'),
        ('rejected', '已拒绝')
    ], string='State', compute='_compute_state')

    @api.depends("validated", "review_ids", "need_validation", "rejected")
    def _compute_state(self):
        for item in self:
            if isinstance(item.id, models.NewId):
                item.depart_state = 'draft'
                item.env['hr.employee'].search([('id', '=', item.employee_id.id)]).write({'employee_status': '1'})
                continue
            if item.need_validation and not item.rejected:
                item.depart_state = 'draft'
                item.env['hr.employee'].search([('id', '=', item.employee_id.id)]).write({'employee_status': '1'})
            elif not item.validated and not item.rejected and item.review_ids:
                item.depart_state = 'pending'
                item.env['hr.employee'].search([('id', '=', item.employee_id.id)]).write({'employee_status': '2'})
            elif item.validated and item.review_ids:
                item.depart_state = 'approved'
                item.env['hr.employee'].search([('id', '=', item.employee_id.id)]).write({'employee_status': '3'})
                self.change_contract()
            elif item.rejected and item.review_ids:
                item.depart_state = 'rejected'
                item.env['hr.employee'].search([('id', '=', item.employee_id.id)]).write({'employee_status': '1'})
            else:
                item.depart_state = 'draft'
                item.env['hr.employee'].search([('id', '=', item.employee_id.id)]).write({'employee_status': '1'})

    def change_contract(self):
        self.employee_id.contract_id.state = 'close'

    @api.model
    def default_get(self, fields):
        defaults = super(TxHrDepart, self).default_get(fields)
        defaults['employee_id'] = self.env.user.employee_id.id
        return defaults
