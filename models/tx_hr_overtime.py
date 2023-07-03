from odoo import fields, models, api
import uuid
from odoo.exceptions import ValidationError


# 加班申请单
class TxHrOvertime(models.Model):
    _name = 'tx.hr.overtime'
    _inherit = 'tier.validation'
    _description = '加班申请单'

    _tier_validation_manual_config = False

    code = fields.Char(string="编号", default=lambda self: self.env['ir.sequence'].next_by_code('tx.hr.overtime'),
                       readonly=True)
    employee_id = fields.Many2one('hr.employee', string='申请人', required=True, readonly=True)
    overtime_person_ids = fields.Many2many('hr.employee', string='加班人员')
    department_id = fields.Many2one('hr.department', string='部门', related='employee_id.department_id', readonly=True)
    employee_job_id = fields.Many2one('hr.job', string='职位', related='employee_id.job_id', readonly=True)
    overtime_type = fields.Selection([('workTime', '工作日'), ('holiday', '节假日')], string='加班类型', default='holiday')
    reason = fields.Text(string='加班内容及计划完成工作量（预计）', required=True)
    start_time = fields.Datetime(string='开始时间', required=True)
    end_time = fields.Datetime(string='结束时间', required=True)
    state = fields.Selection([
        ('draft', '草稿'),
        ('pending', '申请中'),
        ('approved', '审批通过'),
        ('rejected', '已拒绝')
    ], string='State', default='draft')
    overtime_state = fields.Selection([
        ('draft', '草稿'),
        ('pending', '申请中'),
        ('approved', '审批通过'),
        ('rejected', '已拒绝')
    ], string='State', compute='_compute_state')
    attachment_ids = fields.Many2many('ir.attachment', string='附件上传', limit=1)

    def name_get(self):
        result = []
        for record in self:
            name = record.code
            result.append((record.id, name))
        return result

    @api.depends("validated", "review_ids", "need_validation", "rejected")
    def _compute_state(self):
        for item in self:
            if isinstance(item.id, models.NewId):
                item.overtime_state = 'draft'
                continue
            if item.need_validation and not item.rejected:
                item.overtime_state = 'draft'
            elif not item.validated and not item.rejected and item.review_ids:
                item.overtime_state = 'pending'
            elif item.validated and item.review_ids:
                item.overtime_state = 'approved'
            elif item.rejected and item.review_ids:
                item.overtime_state = 'rejected'
            else:
                item.overtime_state = 'draft'

    @api.model
    def default_get(self, fields):
        defaults = super(TxHrOvertime, self).default_get(fields)
        defaults['employee_id'] = self.env.user.employee_id.id
        return defaults

    @api.constrains('overtime_person_ids', 'start_time', 'end_time')
    def _check_employee_overtime(self):
        for record in self:
            overlapping_records = self.env['tx.hr.overtime'].search([
                ('id', '!=', record.id),
                ('overtime_person_ids', 'in', record.overtime_person_ids.ids),
                ('start_time', '<=', record.end_time), ('end_time', '>=', record.start_time),
            ])
            if overlapping_records:
                raise ValidationError("加班人员的开始和结束时间存在重叠记录！")
