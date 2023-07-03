from odoo import fields, models, api
from datetime import datetime
from odoo.exceptions import ValidationError


class PerformanceCoefficient(models.Model):
    _name = "tx.hr.apply.full.member"
    _inherit = 'tier.validation'
    _description = "转正申请表"
    _tier_validation_manual_config = False

    date = fields.Date(string="创建时间", default=datetime.now())
    name = fields.Many2one('hr.employee', string='申请人', required=True, readonly=True)
    department_id = fields.Many2one('hr.department', string='部门', related='name.department_id', readonly=True)
    job_id = fields.Many2one('hr.job', string='职位', related='name.job_id', readonly=True)
    attachment_ids = fields.Many2many('ir.attachment', string='附件上传', limit=1)
    entry_time = fields.Date(string='入职时间', required=True)
    effective_time = fields.Date(string='生效时间', required=True)
    full_member = fields.One2many("tx.hr.apply.full.member.detail", 'name', string="转正人员", required=True)
    pay_increase_category = fields.Selection(
        [('1', '表现优异'), ('2', '升职'), ('3', '年度加薪'), ('4', '薪资调整'), ('5', '转正')],
        string='调薪类别', default='5')
    state = fields.Selection([
        ('draft', '草稿'),
        ('pending', '申请中'),
        ('approved', '审批通过'),
        ('rejected', '已拒绝')
    ], string='状态', default='draft')
    full_state = fields.Selection([
        ('draft', '草稿'),
        ('pending', '申请中'),
        ('approved', '审批通过'),
        ('rejected', '已拒绝')
    ], string='申请状态', compute='_compute_state')

    @api.depends("validated", "review_ids", "need_validation", "rejected")
    def _compute_state(self):
        employee_status_map = {
            'draft': '4',
            'pending': '5',
            'approved': '1',
            'rejected': '4'
        }
        for item in self:
            if isinstance(item.id, models.NewId):
                item.full_state = 'draft'
                continue
            if item.need_validation and not item.rejected:
                item.full_state = 'draft'
            elif not item.validated and not item.rejected and item.review_ids:
                item.full_state = 'pending'
            elif item.validated and item.review_ids:
                item.full_state = 'approved'
            elif item.rejected and item.review_ids:
                item.full_state = 'rejected'
            else:
                item.full_state = 'draft'
            employee_status = employee_status_map.get(item.full_state, '4')
            item.name.employee_status = employee_status

    def button_creat_full_detail(self):
        self.env["tx.hr.apply.full.member.person"].search([]).unlink()
        contract = self.env['hr.employee'].sudo().search([])
        for employee in contract:
            self.env["tx.hr.apply.full.member.person"].create({
                'name': employee.id,
                'department_id': employee.department_id.id,
                'job_id': employee.job_id.id
            })
        return {
            "name": "员工明细",
            "type": "ir.actions.act_window",
            "res_model": 'tx.hr.apply.full.member.person',
            "view_mode": "tree",
            "views": [(self.env.ref('tx_hr.full_member_person_tree').id, "tree")],
            "target": "new",
            "context": {"form_id": self.id},
        }

    @api.model
    def default_get(self, fields):
        defaults = super(PerformanceCoefficient, self).default_get(fields)
        defaults['name'] = self.env.user.employee_id.id
        return defaults


class PerformanceCoefficientDetail(models.Model):
    _name = "tx.hr.apply.full.member.detail"
    name = fields.Many2one("tx.hr.apply.full.member", string='关联id')
    employee_id = fields.Many2one('hr.employee', string='员工', required=True)
    department_id = fields.Many2one('hr.department', string='部门', related='employee_id.department_id', readonly=True)
    job_id = fields.Many2one('hr.job', string='职位', related='employee_id.job_id', readonly=True)
    currentSalary = fields.Float(string='当前薪资', required=True)
    effectiveSalary = fields.Float(string='转正后薪资', required=True)

    @api.constrains('employee_id')
    def _check_employee_salary_deduction(self):
        performance_coefficients = self.env['tx.hr.apply.full.member'].search([('state', '=', 'approved')])
        for performance_coefficient in performance_coefficients:
            for rec in performance_coefficient.performance_coefficient_detail:
                if rec.employee_id.id == self.employee_id.id and rec.id != self.id:
                    raise ValidationError('员工 "%s"已提交一个申请记录' % rec.employee_id.name)


class PerformanceCoefficientPerson(models.TransientModel):
    _name = "tx.hr.apply.full.member.person"
    name = fields.Many2one('hr.employee', string='员工', required=True, readonly=True)
    department_id = fields.Many2one('hr.department', string='部门', related='name.department_id', readonly=True)
    job_id = fields.Many2one('hr.job', string='职位', related='name.job_id', readonly=True)

    def save_data(self):
        record = self.env["tx.hr.apply.full.member.detail"]
        for item in self:
            record.create({
                'name': item.env.context.get('form_id'),
                'employee_id': item.name.id,
                'department_id': item.department_id.id,
                'job_id': item.job_id.id,
                'currentSalary': 0,
                'effectiveSalary': 0,
            })
