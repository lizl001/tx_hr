from datetime import datetime
from dateutil.relativedelta import relativedelta
from odoo import models, fields, api
from odoo.exceptions import ValidationError


class TxHrContract(models.Model):
    _inherit = 'hr.contract'

    # housing_allowance = fields.Float(string='住房补贴', digits=(6, 2))
    post_wage = fields.Float(string='岗位工资', digits=(6, 2))
    performance_pay = fields.Float(string='绩效工资', digits=(6, 2))
    housing_subsidy = fields.Float(string='房补', digits=(6, 2))
    seniority_wage = fields.Integer(string='工龄工资', compute='_compute_seniority_wage', default=0, store=True)
    senior_allowance = fields.Float(string='元老补助', digits=(6, 2))
    job_subsidy = fields.Float(string='岗位津贴', digits=(6, 2))
    social_security = fields.Many2one('tx.hr.social.security', string="社保类型")

    # 计算工龄工资
    @api.depends('date_start')
    def _compute_seniority_wage(self):
        for contract in self:
            if contract.employee_id and contract.date_start:
                now = datetime.now()
                delta = relativedelta(now, contract.date_start)
                seniority = delta.years
                if seniority < 1:
                    contract.seniority_wage = 0
                elif seniority <= 3:
                    contract.seniority_wage = 80 * seniority
                else:
                    contract.seniority_wage = 80 * 3

    @api.constrains('name')
    def check_salary_calculation(self):
        contract = self.env['tx.hr.salary.calculation'].sudo().search([('name', '=', self.employee_id.id)])
        contract.write({
            'wage': self.wage,
            'post_wage': self.post_wage,
            'seniority_pay': self.seniority_wage,
            'merit_pay': self.performance_pay,
            'housing_subsidy': self.housing_subsidy,
            'senior_allowance': self.senior_allowance,
            'job_subsidy': self.job_subsidy,
            'social_security': self.social_security.money
        })


class TxHrEmployee(models.Model):
    _inherit = 'hr.employee'

    bank_card_number = fields.Char(string='银行卡号', groups="hr.group_hr_user")
    opening_bank = fields.Char(string='开户行', groups="hr.group_hr_user")
    employee_status = fields.Selection([
        ('1', '在职'),
        ('2', '离职申请中'),
        ('3', '离职'),
        ('4', '实习'),
        ('5', '转正申请中')],
        string="员工状态",
        default='4',
        groups="hr.group_hr_user"
    )

    @api.constrains('pin')
    def _check_unique_pin(self):
        duplicate_employees = self.search([('pin', '=', self.pin)])
        if len(duplicate_employees) > 1:
            raise ValidationError("PIN must be unique!")

    @api.constrains('name')
    def check_salary_calculation(self):
        contract = self.env['tx.hr.salary.calculation'].sudo()
        contract.create({
            'month': str(datetime.now().today().month),
            'name': self.id,
            'department_id': self.department_id.id,
            'job_id': self.job_id.id
        })
