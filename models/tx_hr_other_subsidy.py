from odoo import fields, models, api
from datetime import datetime
from odoo.exceptions import ValidationError


class OtherSubsidies(models.Model):
    _name = "tx.hr.other.subsidies"
    _description = "其他补助申请"
    _inherit = 'tier.validation'
    _tier_validation_manual_config = False
    date = fields.Date(string="创建时间", default=datetime.now())
    name = fields.Many2one('hr.employee', string='申请人', required=True, readonly=True)
    department_id = fields.Many2one('hr.department', string='部门', related='name.department_id', readonly=True)
    job_id = fields.Many2one('hr.job', string='职位', related='name.job_id', readonly=True)
    deduction_statement = fields.Text(string="补助说明")
    type_deduction = fields.Many2one('tx.hr.subsidy.type', string="补助类型", required=True)
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
    # state = fields.Selection([("confirm", '已确认'), ("draft", '草稿申请')], string='状态', default="draft")
    other_subsidies_detail = fields.One2many("tx.hr.other.subsidies.detail", 'name', string="其他补助明细",
                                             required=True)
    state = fields.Selection([
        ('draft', '草稿'),
        ('pending', '申请中'),
        ('approved', '审批通过'),
        ('rejected', '已拒绝')
    ], string='状态', default='draft')
    other_subsidies_state = fields.Selection([
        ('draft', '草稿'),
        ('pending', '申请中'),
        ('approved', '审批通过'),
        ('rejected', '已拒绝')
    ], string='申请状态', compute='_compute_state')

    @api.depends("validated", "review_ids", "need_validation", "rejected")
    def _compute_state(self):
        for item in self:
            if isinstance(item.id, models.NewId):
                item.other_subsidies_state = 'draft'
                continue
            if item.need_validation and not item.rejected:
                item.other_subsidies_state = 'draft'
            elif not item.validated and not item.rejected and item.review_ids:
                item.other_subsidies_state = 'pending'
            elif item.validated and item.review_ids:
                item.other_subsidies_state = 'approved'
            elif item.rejected and item.review_ids:
                item.other_subsidies_state = 'rejected'
            else:
                item.other_subsidies_state = 'draft'

    @api.model
    def default_get(self, fields):
        defaults = super(OtherSubsidies, self).default_get(fields)
        defaults['name'] = self.env.user.employee_id.id
        return defaults

    def button_creat_coefficient_detail(self):
        self.env["tx.hr.other.subsidies.person"].search([]).unlink()
        employees = self.env['hr.employee'].sudo().search([])
        for employee in employees:
            self.env["tx.hr.other.subsidies.person"].create({
                'name': employee.id,
                'department_id': employee.department_id.id,
                'job_id': employee.job_id.id
            })
        return {
            "name": "员工明细",
            "type": "ir.actions.act_window",
            "res_model": "tx.hr.other.subsidies.person",
            "view_mode": "tree",
            "views": [(self.env.ref('tx_hr.other_subsidies_person_tree').id, "tree")],
            "target": "new",
            "context": {"form_id": self.id},
        }


class PieceRateDetail(models.Model):
    _name = "tx.hr.other.subsidies.detail"
    name = fields.Many2one("tx.hr.other.subsidies", string='关联id')
    employee_id = fields.Many2one('hr.employee', string='员工', required=True)
    department_id = fields.Many2one('hr.department', string='部门', related='employee_id.department_id')
    job_id = fields.Many2one('hr.job', string='职位', related='employee_id.job_id')
    amount_subsidy = fields.Float(string="补助金额", required=True)

    # @api.constrains('name', 'employee_id', 'department_id')
    # def _check_employee_salary_deduction(self):
    #     for rec in self:
    #         domain = [
    #             ('name', '=', rec.name.id),
    #             ('employee_id', '=', rec.employee_id.id),
    #             ('department_id', '=', rec.department_id.id),
    #             ('id', '!=', rec.id),
    #         ]
    #         if self.search_count(domain) > 0:
    #             raise ValidationError('员工 "%s"已提交一个申请记录' % (rec.name.name.name))


class PieceRatePerson(models.TransientModel):
    _name = "tx.hr.other.subsidies.person"
    name = fields.Many2one('hr.employee', string='员工', required=True, readonly=True)
    department_id = fields.Many2one('hr.department', string='部门', related='name.department_id', readonly=True)
    job_id = fields.Many2one('hr.job', string='职位', related='name.job_id', readonly=True)

    def save_data(self):
        record = self.env["tx.hr.other.subsidies.detail"]
        for item in self:
            record.create({
                'name': item.env.context.get('form_id'),
                'employee_id': item.name.id,
                'department_id': item.department_id.id,
                'job_id': item.job_id.id,
                'amount_subsidy': 0
            })


class SubsidyType(models.Model):
    _name = "tx.hr.subsidy.type"
    _description = '补助类型'

    name = fields.Char(string='类型')
