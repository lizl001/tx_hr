import datetime

from odoo import fields, models, api
import uuid

from odoo.addons.base_tier_validation.models.tier_validation import TierValidation
from odoo.exceptions import ValidationError


# 出差申请单
class TxHrBusinessTrip(models.Model):
    _name = "tx.hr.business.trip"
    _inherit = 'tier.validation'
    _description = "出差申请"

    _tier_validation_manual_config = False

    employee_id = fields.Many2one('hr.employee', string='申请人', required=True, readonly=True)
    pin = fields.Char(string='工号', readonly=True, related='employee_id.pin', store=True)
    department_id = fields.Many2one('hr.department', string='部门', related='employee_id.department_id', readonly=True,
                                    store=True)
    employee_job_id = fields.Many2one('hr.job', string='职位', related='employee_id.job_id', readonly=True)
    explain = fields.Text(string="说明")
    begin_time = fields.Date(string="开始时间", required=True)
    over_time = fields.Date(string="结束时间", required=True)
    attachment_ids = fields.Many2many('ir.attachment', string='附件上传', limit=1)
    state = fields.Selection([
        ('draft', '草稿'),
        ('pending', '申请中'),
        ('approved', '审批通过'),
        ('rejected', '已拒绝')
    ], string='State', default='draft')
    business_state = fields.Selection([
        ('draft', '草稿'),
        ('pending', '申请中'),
        ('approved', '审批通过'),
        ('rejected', '已拒绝')
    ], string='State', compute='_compute_state')
    attachment_ids = fields.Many2many('ir.attachment', string='附件上传', limit=1)
    business_person_ids = fields.Many2many('hr.employee', string='出差人员')
    business_approve = fields.Boolean(string='是否已经审批', default=False)

    @api.depends("validated", "review_ids", "need_validation", "rejected")
    def _compute_state(self):
        for item in self:
            if isinstance(item.id, models.NewId):
                item.business_state = 'draft'
                continue
            if item.need_validation and not item.rejected:
                item.business_state = 'draft'
            elif not item.validated and not item.rejected and item.review_ids:
                item.business_state = 'pending'
            elif item.validated and item.review_ids:
                if not item.business_approve:
                    self.add_work_time()
                    item.business_approve = True
                item.business_state = 'approved'
            elif item.rejected and item.review_ids:
                item.business_state = 'rejected'
            else:
                item.business_state = 'draft'

    def write(self, vals):
        for rec in self:
            return super(TierValidation, self).write(vals)

    def add_work_time(self):
        current_date = self.begin_time  # 获取开始时间的日期部分
        end_date = self.over_time  # 获取结束时间的日期部分

        for person in self.business_person_ids:
            # 日报记录
            while current_date <= end_date:
                add_attendance_time = 0
                # 查询该员工当天是否有打卡记录
                record = self.env['tx.hr.attendance.daily'].search(
                    [('employee_id', '=', person.id), ('date', '=', current_date)], limit=1)
                if record:
                    add_attendance_time = 1 - record.attendance_time
                    record.attendance_time = 1
                    self.env['tx.hr.attendance.daily'].write(record)
                else:
                    attend_record = {
                        'employee_id': person.id,
                        'pin': person.pin,
                        'date': current_date,
                        'year': current_date.year,
                        'month': current_date.month,
                        'late_leave_early': 0,
                        'attendance_time': 1
                    }
                    self.env['tx.hr.attendance.daily'].create(attend_record)

                # 月报
                emp_month_attendance = self.env['tx.hr.attendance.monthly'].search(
                    [('year', '=', current_date.year),
                     ('month', '=', current_date.month),
                     ('employee.id', '=', person.id)])
                if emp_month_attendance:
                    emp_month_attendance.write(
                        {'attendance_time': emp_month_attendance.attendance_time + add_attendance_time})
                else:
                    emp_month_attendance_record = {
                        'employee': person.id,
                        'pin': person.pin,
                        'year': current_date.year,
                        'month': current_date.month,
                        'late_leave_early': 0,
                        'attendance_time': 1
                    }
                    self.env['tx.hr.attendance.monthly'].create(emp_month_attendance_record)
                # 增加一天，以便遍历下一个日期
                current_date += datetime.timedelta(days=1)

    @api.constrains('business_person_ids', 'begin_time', 'over_time')
    def _check_employee_leave(self):
        for record in self:
            overlapping_records = self.env['tx.hr.business.trip'].search([
                ('id', '!=', record.id),
                ('business_person_ids', 'in', record.business_person_ids.ids),
                ('begin_time', '<=', record.over_time), ('over_time', '>=', record.begin_time),
            ])
            if overlapping_records:
                raise ValidationError("出差人员的开始和结束时间存在重叠记录！")

    @api.model
    def default_get(self, fields):
        defaults = super(TxHrBusinessTrip, self).default_get(fields)
        defaults['employee_id'] = self.env.user.employee_id.id
        return defaults
