from odoo import fields, models, api
from datetime import datetime, timedelta, date
from dateutil import relativedelta


class FillingFactor(models.Model):
    _name = "tx.hr.filling.factor"
    _description = '补卡系数'

    filling_factor = fields.Integer(string="补卡系数", default=3)

    def init(self):
        if not self.search([], limit=1):
            self.create({
                'filling_factor': 3,
            })


class CardReplacementTimeRange(models.Model):
    _name = "tx.hr.card.time.range"
    _description = '补卡时间范围'

    card_time_range = fields.Integer(string="补卡时间范围", help="单位：天")

    def init(self):
        if not self.search([], limit=1):
            self.create({
                'card_time_range': 3,
            })


class CardReplacementApplication(models.Model):
    _name = "tx.hr.card.replacement.application"
    _description = '补卡申请'
    _inherit = 'tier.validation'
    _tier_validation_manual_config = False

    proposer_employee_id = fields.Many2one('hr.employee', string="申请人",
                                           default=lambda self: self.env.user.employee_id.id)
    proposer_department_id = fields.Many2one('hr.department', string="申请人部门",
                                             related="proposer_employee_id.department_id")
    proposer_job_id = fields.Many2one('hr.job', string='申请人职位', related="proposer_employee_id.job_id")
    reason = fields.Text(string="补卡原因")
    attachment_ids = fields.Many2many('ir.attachment', string='附件上传', limit=1)
    card_detail_ids = fields.One2many('tx.hr.card.replacement.application.detail', 'card_replacement_application_id',
                                      string="补卡人员明细")
    employee_id = fields.Many2one('hr.employee', string="员工", default=lambda self: self.env.user.employee_id.id)
    department_id = fields.Many2one('hr.department', string="部门", related="employee_id.department_id")
    job_id = fields.Many2one('hr.job', string='职位', related="employee_id.job_id")
    state = fields.Selection([
        ('draft', '草稿'),
        ('pending', '申请中'),
        ('approved', '审批通过'),
        ('rejected', '已拒绝')
    ], string='状态', default='draft')
    card_rate_state = fields.Selection([
        ('draft', '草稿'),
        ('pending', '申请中'),
        ('approved', '审批通过'),
        ('rejected', '已拒绝')
    ], string='申请状态', compute='_compute_state')

    @api.depends("validated", "review_ids", "need_validation", "rejected")
    def _compute_state(self):
        for item in self:
            if isinstance(item.id, models.NewId):
                item.card_rate_state = 'draft'
                continue
            if item.need_validation and not item.rejected:
                item.card_rate_state = 'draft'
            elif not item.validated and not item.rejected and item.review_ids:
                item.card_rate_state = 'pending'
            elif item.validated and item.review_ids:
                item.card_rate_state = 'approved'
            elif item.rejected and item.review_ids:
                item.card_rate_state = 'rejected'
            else:
                item.card_rate_state = 'draft'

    @api.depends("state")
    def _compute_validated(self):
        if self.state == 'approved':
            for item in self.card_detail_ids:
                day = (item.begin_time - item.end_time).total_seconds() / 3600 / 8
                monthly_employee = self.env['tx.hr.attendance.monthly'].search([('year', '=', datetime.now().year),
                                                                                ('month', '=', datetime.now().month),
                                                                                ('employee.id', '=', item.employee_id)])
                if monthly_employee:
                    monthly_employee.write({
                        'attendance_time': monthly_employee.attendance_time + day
                    })

    def button_creat_application_detail(self):
        self.env['tx.hr.card.replacement.application.person'].search([]).unlink()
        employees = self.env['hr.employee'].sudo().search([])
        for employee in employees:
            self.env["tx.hr.card.replacement.application.person"].create({
                'employee_id': employee.id,
                'department_id': employee.department_id.id,
                'job_id': employee.job_id.id
            })
        return {
            "name": "员工明细",
            "type": "ir.actions.act_window",
            "res_model": 'tx.hr.card.replacement.application.person',
            "view_mode": "tree",
            "views": [(self.env.ref('tx_hr.card_replacement_application_person_tree').id, "tree")],
            "target": "new",
            "context": {"form_id": self.id},
        }


class CardReplacementApplicationDetail(models.Model):
    _name = 'tx.hr.card.replacement.application.detail'
    _description = '补卡申请明细'

    card_replacement_application_id = fields.Many2one('tx.hr.card.replacement.application', string="补卡申请")
    employee_id = fields.Many2one('hr.employee', string="员工", default=lambda self: self.env.user.employee_id.id)
    department_id = fields.Many2one('hr.department', string="部门", related="employee_id.department_id")
    job_id = fields.Many2one('hr.job', string='职位', related="employee_id.job_id")
    begin_time = fields.Datetime(string="补卡开始时间")
    end_time = fields.Datetime(string="补卡结束时间")

    @api.constrains('begin_time', 'end_time')
    def _check_time(self):
        time_range = self.env['tx.hr.card.time.range'].search([], limit=1).card_time_range
        for item in self:
            if item.begin_time > item.end_time:
                raise models.ValidationError("补卡开始时间不能大于补卡结束时间")
            if item.end_time > datetime.now():
                raise models.ValidationError("补卡结束时间不能大于当前时间")
            three_days_ago = datetime.now() - timedelta(days=time_range)
            if item.begin_time < three_days_ago:
                raise models.ValidationError('补卡时间需要在 "%s" 天范围内' % time_range)
            if item.end_time > datetime.now():
                raise models.ValidationError('补卡结束不能超过当前时间')

    @api.constrains('employee_id')
    def _check_employee(self):
        filling_factor = self.env['tx.hr.filling.factor'].search([]).filling_factor
        for item in self:
            year = date.today().year
            month = date.today().month
            first_day = datetime(year, month, 1, 0, 0, 0)
            if month == 12:
                last_day = datetime(year, month, 31, 0, 0, 0, 0)
            else:
                last_day = datetime(year, month + 1, 1, 0, 0, 0) - timedelta(days=1)
            record_count = self.env['tx.hr.card.replacement.application.detail'].search_count(
                [('employee_id', '=', item.employee_id.id),
                 ('begin_time', '>=', first_day),
                 ('end_time', '<=', last_day)
                 ])
            if record_count + 1 > filling_factor:
                raise models.ValidationError('"%s"补卡次数已超过"%s"次' % (item.employee_id.name, filling_factor))


class CardReplacementApplicationPerson(models.Model):
    _name = 'tx.hr.card.replacement.application.person'
    _description = '补卡申请人员'
    employee_id = fields.Many2one('hr.employee', string="员工", default=lambda self: self.env.user.employee_id.id)
    department_id = fields.Many2one('hr.department', string="部门", related="employee_id.department_id")
    job_id = fields.Many2one('hr.job', string='职位', related="employee_id.job_id")

    def save_data(self):
        record = self.env["tx.hr.card.replacement.application.detail"]
        for item in self:
            record.create({
                'card_replacement_application_id': item.env.context.get('form_id'),
                'employee_id': item.employee_id.id,
                'department_id': item.department_id.id,
                'job_id': item.job_id.id,
            })
