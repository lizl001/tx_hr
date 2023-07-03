from odoo import fields, models, api
from datetime import datetime
from odoo.exceptions import ValidationError

class PerformanceCoefficient(models.Model):
    _name = "tx.hr.performance.coefficient"
    _inherit = 'tier.validation'
    _description = "绩效系数申请"
    _tier_validation_manual_config = False
    # pin = fields.Char(string='工号', readonly=True, related='name.pin', store=True)
    date = fields.Date(string="创建时间", default=datetime.now())
    name = fields.Many2one('hr.employee', string='申请人', required=True, readonly=True)
    department_id = fields.Many2one('hr.department', string='部门', related='name.department_id', readonly=True)
    job_id = fields.Many2one('hr.job', string='职位', related='name.job_id', readonly=True)
    performance_coefficient_detail = fields.One2many("tx.hr.performance.coefficient.detail", 'name', string="绩效明细",
                                                     required=True)
    attachment_ids = fields.Many2many('ir.attachment', string='附件上传', limit=1)
    year = fields.Selection(
        [(str(year), str(year) + '年') for year in range(date.today().year - 10, date.today().year + 10)],
        string='年份',
        required=True,
        default=str(date.today().year)
    )
    month = fields.Selection(
        [(str(month), str(month) + '月') for month in range(1, 13)],
        string='月份',
        required=True,
        default=str(date.today().month)
    )
    state = fields.Selection([
        ('draft', '草稿'),
        ('pending', '申请中'),
        ('approved', '审批通过'),
        ('rejected', '已拒绝')
    ], string='状态', default='draft')
    performance_state = fields.Selection([
        ('draft', '草稿'),
        ('pending', '申请中'),
        ('approved', '审批通过'),
        ('rejected', '已拒绝')
    ], string='申请状态', compute='_compute_state')

    @api.depends("validated", "review_ids", "need_validation", "rejected")
    def _compute_state(self):
        for item in self:
            if isinstance(item.id, models.NewId):
                item.performance_state = 'draft'
                continue
            if item.need_validation and not item.rejected:
                item.performance_state = 'draft'
            elif not item.validated and not item.rejected and item.review_ids:
                item.performance_state = 'pending'
            elif item.validated and item.review_ids:
                item.performance_state = 'approved'
            elif item.rejected and item.review_ids:
                item.performance_state = 'rejected'
            else:
                item.performance_state = 'draft'

    # @api.constrains('name', 'year', 'month')
    # def _check_employee_salary_deduction(self):
    #     for rec in self:
    #         domain = [
    #             ('name', '=', rec.name.id),
    #             ('year', '=', rec.year),
    #             ('month', '=', rec.month),
    #             ('id', '!=', rec.id),
    #         ]
    #         if self.search_count(domain) > 0:
    #             raise ValidationError('员工 "%s" %s 年 %s 月已提交一个申请记录' % (rec.name.name, rec.year, rec.month))

    def button_creat_coefficient_detail(self):
        self.env["tx.hr.performance.coefficient.person"].search([]).unlink()
        contract = self.env['hr.employee'].sudo().search([])
        for employee in contract:
            self.env["tx.hr.performance.coefficient.person"].create({
                'name': employee.id,
                'department_id': employee.department_id.id,
                'job_id': employee.job_id.id
            })
        return {
            "name": "员工明细",
            "type": "ir.actions.act_window",
            "res_model": 'tx.hr.performance.coefficient.person',
            "view_mode": "tree",
            "views": [(self.env.ref('tx_hr.view_performance_coefficient_person_tree').id, "tree")],
            "target": "new",
            "context": {"form_id": self.id},
        }

    @api.model
    def default_get(self, fields):
        defaults = super(PerformanceCoefficient, self).default_get(fields)
        defaults['name'] = self.env.user.employee_id.id
        return defaults


class PerformanceCoefficientDetail(models.Model):
    _name = "tx.hr.performance.coefficient.detail"
    name = fields.Many2one("tx.hr.performance.coefficient", string='关联id')
    employee_id = fields.Many2one('hr.employee', string='员工', required=True)
    department_id = fields.Many2one('hr.department', string='部门', related='employee_id.department_id', readonly=True)
    job_id = fields.Many2one('hr.job', string='职位', related='employee_id.job_id', readonly=True)
    amount_subsidy = fields.Float(string="绩效系数")

    @api.constrains('employee_id')
    def _check_employee_salary_deduction(self):
        performance_coefficients = self.env['tx.hr.performance.coefficient'].search(
            [('month', '=', datetime.now().month), ('year', '=', datetime.now().year), ('state', '=', 'approved')])
        for performance_coefficient in performance_coefficients:
            for rec in performance_coefficient.performance_coefficient_detail:
                if rec.employee_id.id == self.employee_id.id and rec.id != self.id:
                    raise ValidationError('员工 "%s"已提交一个申请记录' % rec.employee_id.name)
    # for rec in self:
    #     domain = [
    #         ('name', '=', rec.name.id),
    #         ('employee_id', '=', rec.employee_id.id),
    #         ('department_id', '=', rec.department_id.id),
    #         ('id', '!=', rec.id),
    #     ]
    #     if self.search_count(domain) > 0:
    #         raise ValidationError('员工 "%s"已提交一个申请记录' % (rec.name.name.name))


class PerformanceCoefficientPerson(models.TransientModel):
    _name = "tx.hr.performance.coefficient.person"
    name = fields.Many2one('hr.employee', string='员工', required=True, readonly=True)
    department_id = fields.Many2one('hr.department', string='部门', related='name.department_id', readonly=True)
    job_id = fields.Many2one('hr.job', string='职位', related='name.job_id', readonly=True)

    def save_data(self):
        record = self.env["tx.hr.performance.coefficient.detail"]
        for item in self:
            record.create({
                'name': item.env.context.get('form_id'),
                'employee_id': item.name.id,
                'department_id': item.department_id.id,
                'job_id': item.job_id.id,
                'amount_subsidy': 0
            })
