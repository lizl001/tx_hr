from datetime import datetime
from odoo.exceptions import ValidationError
from odoo import fields, models, api


class HrLeave(models.Model):
    _name = "tx.hr.leave"
    _description = "请假申请"
    _inherit = 'tier.validation'
    _tier_validation_manual_config = False
    date = fields.Date(string="创建时间", default=datetime.now())
    name = fields.Many2one('hr.employee', string='申请人', required=True, readonly=True)
    department_id = fields.Many2one('hr.department', string='部门', related='name.department_id', readonly=True)
    job_id = fields.Many2one('hr.job', string='职位', related='name.job_id', readonly=True)
    leave_explain = fields.Text(string="说明")
    begin_time = fields.Datetime(string="开始时间", required=True)
    over_time = fields.Datetime(string="结束时间", required=True)
    leave_type = fields.Selection([("1", '事假'), ("2", '病假')], string='请假类型', required=True)
    attachment_ids = fields.Many2many('ir.attachment', string='附件上传')
    leave_person_ids = fields.Many2many('hr.employee', string='员工', required=True)
    state = fields.Selection([
        ('draft', '草稿'),
        ('pending', '申请中'),
        ('approved', '审批通过'),
        ('rejected', '已拒绝')
    ], string='状态', default='draft')
    leave_state = fields.Selection([
        ('draft', '草稿'),
        ('pending', '申请中'),
        ('approved', '审批通过'),
        ('rejected', '已拒绝')
    ], string='申请状态', compute='_compute_state')

    @api.depends("validated", "review_ids", "need_validation", "rejected")
    def _compute_state(self):
        for item in self:
            if isinstance(item.id, models.NewId):
                item.leave_state = 'draft'
                continue
            if item.need_validation and not item.rejected:
                item.leave_state = 'draft'
            elif not item.validated and not item.rejected and item.review_ids:
                item.leave_state = 'pending'
            elif item.validated and item.review_ids:
                item.leave_state = 'approved'
            elif item.rejected and item.review_ids:
                item.leave_state = 'rejected'
            else:
                item.leave_state = 'draft'

    @api.constrains('name', 'begin_time', 'over_time')
    def _check_employee_leave(self):
        for rec in self:
            domain = [
                ('name', '=', rec.name.id),
                ('begin_time', '<', rec.over_time),
                ('over_time', '>', rec.begin_time),
                ('id', '!=', rec.id),
            ]
            if self.search_count(domain) > 0:
                raise ValidationError('员工 "%s" 在这个时间段内已经提交了一条请假记录' % rec.name.name)

    # def action_confirm(self):
    #     if self.state == 'draft':
    #         self.state = 'confirm'

    @api.model
    def default_get(self, fields):
        defaults = super(HrLeave, self).default_get(fields)
        defaults['name'] = self.env.user.employee_id.id
        return defaults
