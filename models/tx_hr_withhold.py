from odoo import fields, models, api
from datetime import datetime
from odoo.exceptions import ValidationError


class Withhold(models.Model):
    _name = "tx.hr.withhold"
    _inherit = 'tier.validation'
    _description = '扣款申请单'
    _tier_validation_manual_config = False

    date = fields.Date(string="创建时间", default=datetime.now())
    name = fields.Many2one('hr.employee', string='申请人', required=True, readonly=True)
    department_id = fields.Many2one('hr.department', string='部门', related='name.department_id', readonly=True)
    job_id = fields.Many2one('hr.job', string='职位', related='name.job_id', readonly=True)
    deduction_statement = fields.Text(string="扣款说明")
    type_deduction = fields.Char(string="扣款类型", required=True)
    attachment_ids = fields.Many2many('ir.attachment', string='附件上传', limit=1)
    year = fields.Selection(
        [(str(year), str(year) + '年') for year in range(datetime.now().year - 10, datetime.now().year + 10)],
        string='年份',
        required=True,
        default=str(datetime.now().year)
    )
    month = fields.Selection(
        [(str(month), str(month) + '月') for month in range(1, 13)],
        string='月份',
        required=True,
        default=str(datetime.now().month)
    )
    # state = fields.Selection([("confirm", '已确认'), ("draft", '草稿申请')], string='状态', default="draft")
    withhold_detail = fields.One2many("tx.hr.withhold.detail", 'name', string="扣款明细", required=True)

    state = fields.Selection([
        ('draft', '草稿'),
        ('pending', '申请中'),
        ('approved', '审批通过'),
        ('rejected', '已拒绝')
    ], string='状态', default='draft')
    withhold_state = fields.Selection([
        ('draft', '草稿'),
        ('pending', '申请中'),
        ('approved', '审批通过'),
        ('rejected', '已拒绝')
    ], string='申请状态', compute='_compute_state')

    @api.depends("validated", "review_ids", "need_validation", "rejected")
    def _compute_state(self):
        for item in self:
            if isinstance(item.id, models.NewId):
                item.withhold_state = 'draft'
                continue
            if item.need_validation and not item.rejected:
                item.withhold_state = 'draft'
            elif not item.validated and not item.rejected and item.review_ids:
                item.withhold_state = 'pending'
            elif item.validated and item.review_ids:
                item.withhold_state = 'approved'
            elif item.rejected and item.review_ids:
                item.withhold_state = 'rejected'
            else:
                item.withhold_state = 'draft'

    @api.model
    def default_get(self, fields):
        defaults = super(Withhold, self).default_get(fields)
        defaults['name'] = self.env.user.employee_id.id
        return defaults

    def button_creat_coefficient_detail(self):
        self.env["tx.hr.withhold.person"].search([]).unlink()
        contract = self.env['hr.employee'].sudo().search([])
        withhold_person_vals = []
        for employee in contract:
            withhold_person_vals.append({
                'name': employee.id,
                'department_id': employee.department_id.id,
                'job_id': employee.job_id.id
            })
        self.env["tx.hr.withhold.person"].create(withhold_person_vals)
        return {
            "name": "员工明细",
            "type": "ir.actions.act_window",
            "res_model": 'tx.hr.withhold.person',
            "view_mode": "tree",
            "views": [(self.env.ref('tx_hr.withhold_person_tree').id, "tree")],
            "target": "new",
            "context": {"form_id": self.id},
        }


class WithholdDetail(models.Model):
    _name = "tx.hr.withhold.detail"
    name = fields.Many2one('tx.hr.withhold', string='关联id')
    employee_id = fields.Many2one('hr.employee', string='员工', required=True)
    department_id = fields.Many2one('hr.department', string='部门', related='employee_id.department_id', readonly=True)
    job_id = fields.Many2one('hr.job', string='职位', related='employee_id.job_id', readonly=True)
    amount_subsidy = fields.Float(string="扣款金额", required=True)

    # @api.constrains('name', 'employee_id', 'department_id')
    # def _check_employee_salary_deduction(self):
    #     domain = [
    #         ('name', '=', self.name.id),
    #         ('employee_id', '=', self.employee_id.id),
    #         ('department_id', '=', self.department_id.id),
    #         ('id', '!=', self.id),
    #     ]
    #     if self.search_count(domain) > 0:
    #         raise ValidationError('员工 "%s"已提交一个申请记录' % (self.name.name.name))


class WithholdPerson(models.TransientModel):
    _name = "tx.hr.withhold.person"
    name = fields.Many2one('hr.employee', string='员工', required=True, readonly=True)
    department_id = fields.Many2one('hr.department', string='部门', related='name.department_id', readonly=True)
    job_id = fields.Many2one('hr.job', string='职位', related='name.job_id', readonly=True)

    # def save_data(self):
    #     withhold_detail_obj = self.env["tx.hr.withhold.detail"]
    #     withhold_details = []
    #     for item in self:
    #         withhold_details.append({
    #             'name': item.env.context.get('form_id'),
    #             'employee_id': item.name.id,
    #             'department_id': item.department_id.id,
    #             'job_id': item.job_id.id,
    #             'amount_subsidy': 0
    #         })
    #     withhold_detail_obj.create(withhold_details)
    def save_data(self):
        record = self.env["tx.hr.withhold.detail"]
        for item in self:
            record.create({
                'name': item.env.context.get('form_id'),
                'employee_id': item.name.id,
                'department_id': item.department_id.id,
                'job_id': item.job_id.id,
                'amount_subsidy': 0
            })
