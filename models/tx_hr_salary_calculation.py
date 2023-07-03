from odoo import models, fields, api
import datetime
from odoo.exceptions import ValidationError


class IndividualIncomeTax(models.Model):
    _name = "tx.hr.individual_income_tax"
    _description = "个人减免额度"

    name = fields.Many2one('hr.employee', string='员工', required=True)
    department_id = fields.Many2one('hr.department', string='部门', related='name.department_id', readonly=True)
    job_id = fields.Many2one('hr.job', string='职位', related='name.job_id', readonly=True)
    employee_id = fields.Many2one('hr.employee', string="员工")
    children_education = fields.Float("子女教育")
    adult_education = fields.Float("继续教育")
    treatment_serious_disease = fields.Float("大病医疗")
    housing_loan_interest = fields.Float("住房贷款利息")
    housing_rent = fields.Float("住房租金")
    support_old = fields.Float("赡养老人")
    individual_income_sum = fields.Float("减免额度总和", compute="compute_for_individual_income", store=True)

    @api.constrains('employee_id')
    def employee_leave(self):
        for rec in self:
            domain = [
                ('name', '=', rec.name.id),
                ('id', '!=', rec.id),
            ]
            if self.search_count(domain) > 0:
                raise ValidationError('员工 "%s" 已经有记录' % rec.name.name)

    @api.depends('children_education', 'adult_education', 'treatment_serious_disease', 'housing_loan_interest',
                 'housing_rent', 'support_old')
    def compute_for_individual_income(self):
        for record in self:
            record.individual_income_sum = record.children_education + record.adult_education + record.treatment_serious_disease + record.housing_loan_interest + record.housing_rent + record.support_old


class OvertimeRate(models.Model):
    _name = "tx.hr.overtime.rate"
    _description = "加班工资比例"

    regular_overtime_pay = fields.Integer(string='正常加班工资', default=15)
    holiday_overtime_pay = fields.Integer(string='节假日加班工资', default=18)

    def init(self):
        if not self.search([], limit=1):
            self.create({
                'regular_overtime_pay': 15,
                'holiday_overtime_pay': 18,
            })


class SalaryCalculation(models.Model):
    _name = 'tx.hr.salary.calculation'
    _description = '工资计算'

    date = fields.Date(string="创建时间", default=datetime.datetime.now())
    year = fields.Selection(
        [(str(year), str(year) + '年') for year in range(date.today().year - 10, date.today().year + 10)],
        string='年份', required=True, default=str(date.today().year), readonly=True)
    month = fields.Selection([(str(month), str(month) + '月') for month in range(1, 13)], string='月份', required=True,
                             default=str(date.today().month), readonly=True)
    name = fields.Many2one('hr.employee', string='员工', required=True, readonly=True)
    department_id = fields.Many2one('hr.department', string='部门', related='name.department_id', readonly=True)
    job_id = fields.Many2one('hr.job', string='职位', related='name.job_id', readonly=True)
    other_subsidies = fields.Float(string="其他补助", readonly=True)
    piece_rate = fields.Float(string="计件工资", readonly=True)
    performance_coefficient = fields.Float(string="绩效系数", readonly=True)
    deduction = fields.Float(string="扣款金额", readonly=True)
    days_of_attendance_due = fields.Integer(string='应出勤天数', readonly=True)
    normal_overtime_hours = fields.Float(string="正常加班时长", readonly=True)
    holiday_overtime_hours = fields.Float(string="节假加班时长", readonly=True)
    regular_overtime_pay = fields.Float(string="正常加班工资", readonly=True)
    holiday_overtime_pay = fields.Float(string="节假加班工资", readonly=True)
    attendance = fields.Float(string="出勤天数", readonly=True)
    overtime_pay = fields.Float(string="劳务加班工资", readonly=True)
    attendance_bonus = fields.Float(string="全勤奖", readonly=True)
    total_wage_bill = fields.Float(string="工资总额", readonly=True)
    social_security = fields.Float(string="社保", readonly=True, store=True)
    individual_income_tax = fields.Float(string="个税", readonly=True, )
    wages_payable = fields.Float(string="应付工资", readonly=True, store=True)
    net_pay = fields.Float(string="实付工资", readonly=True)
    wage = fields.Integer(string="基本工资", readonly=True)
    post_wage = fields.Float(string="岗位工资", readonly=True)
    seniority_pay = fields.Integer(string="工龄工资", readonly=True)
    merit_pay = fields.Float(string="绩效工资", readonly=True)
    housing_subsidy = fields.Float(string="房补", readonly=True)
    senior_allowance = fields.Float(string="元老补助", readonly=True)
    job_subsidy = fields.Float(string="岗位津贴", readonly=True)
    # 归档
    active = fields.Boolean(default=True)

    @api.constrains('name')
    def run_main(self):
        # 总方法调用全部方法，便于逻辑修改和问题定位
        for record in self:
            holiday_overtime_rite, regular_overtime_rite = record.get_overtime_rite()
            days_of_attendance_due = record.get_days_of_attendance_due()  # 应出勤天数
            # 出勤天数,全勤奖,加班时长,节假日加班时长
            attendance, attendance_bonus, normal_overtime_hours, holiday_overtime_hours = record.count_attendance()
            performance_coefficient = record.get_performance_coefficient()  # 绩效系数
            piece_rate = record.get_piece_rate()  # 计件工资
            other_subsidies = record.get_other_subsidies()  # 其他补助
            deduction = record.get_deduction()  # 扣款金额
            # 工龄工资 住房补贴 元老补助 岗位津贴 社保
            seniority_pay, housing_subsidy, senior_allowance, job_subsidy, social_security = record.get_wage()
            # 基本工资,岗位工资 住房补贴
            wage, post_wage, housing_subsidy = record.payroll_computation(days_of_attendance_due, attendance)
            merit_pay = record.merit_pay_calculation(performance_coefficient)  # 绩效工资
            regular_overtime_pay = record.get_regular_overtime_pay(normal_overtime_hours,
                                                                   regular_overtime_rite)  # 正常加班工资
            holiday_overtime_pay = record.get_holiday_overtime_pay(holiday_overtime_hours,
                                                                   holiday_overtime_rite)  # 节假加班工资
            total_wage_bill = record.get_total_wage_bill(wage, post_wage, merit_pay, piece_rate, seniority_pay,
                                                         regular_overtime_pay, holiday_overtime_pay, attendance_bonus,
                                                         other_subsidies, senior_allowance, job_subsidy,
                                                         housing_subsidy)  # 基本工资
            wages_payable = record.get_wages_payable(total_wage_bill, deduction)  # 应付工资
            individual_income_tax = record.get_individual_income_tax(social_security)  # 计算个税
            record.calculate_net_pay(wages_payable, social_security, individual_income_tax)  # 实付工资 应付工资-社保-个税

    # 计算获取加班工资比例
    def get_overtime_rite(self):
        holiday_overtime_rite = self.env["tx.hr.overtime.rate"].search([], limit=1).holiday_overtime_pay
        regular_overtime_rite = self.env["tx.hr.overtime.rate"].search([], limit=1).regular_overtime_pay
        return holiday_overtime_rite, regular_overtime_rite

    # 应出勤天数 根据节假日表获取下月的应出勤天数
    def get_days_of_attendance_due(self):
        char = self.env["tx.hr.scheduling"].sudo().search(
            [('year', '=', self.year), ('name.id', '=', self.name.id), ('month', '=', self.month)], limit=1)
        self.days_of_attendance_due = char.days_of_attendance_due
        return self.days_of_attendance_due

    # 获取出勤天数和上班时间和加班时间，计算是否获得全勤奖
    def count_attendance(self):
        record = self.env['tx.hr.attendance.monthly'].sudo().search(
            [('employee', '=', self.name.id), ('year', '=', self.year), ('month', '=', self.month)])
        if record:
            self.attendance = record.attendance_time
            self.normal_overtime_hours = record.normal_overtime_hours
            self.holiday_overtime_hours = record.holiday_overtime_hours
            if record.attendance_time == self.days_of_attendance_due or record.late_leave_early > 5:
                self.attendance_bonus = 100
            else:
                self.attendance_bonus = 0
        return self.attendance, self.attendance_bonus, self.normal_overtime_hours, self.holiday_overtime_hours

    # 获取指定模型的指定字段的值
    def _get_field_value(self, model, field, employee_id, state):
        obj = self.env[model].sudo().search([
            ('year', '=', self.year),
            ('month', '=', self.month),
            (state, '=', 'approved')
        ])
        amount_subsidy = 0
        if obj and obj[field]:
            for detail in obj[field]:
                if employee_id == detail.employee_id.id:
                    amount_subsidy += detail.amount_subsidy
            return amount_subsidy
        return 0

    # 绩效系数 绩效系数申请通过后获取绩效系数
    def get_performance_coefficient(self):
        self.performance_coefficient = self._get_field_value('tx.hr.performance.coefficient',
                                                             'performance_coefficient_detail', self.name.id,
                                                             'performance_state')
        return self.performance_coefficient

    # 计件工资 计件工资申请通过后获取原有基础+计件工资申请
    def get_piece_rate(self):
        self.piece_rate = self._get_field_value('tx.hr.piece.rate', 'piece_rate_detail', self.name.id,
                                                'piece_rate_state')
        return self.piece_rate

    # 其他补助 其他补助申请通过后获取其他补助
    def get_other_subsidies(self):
        self.other_subsidies = self._get_field_value('tx.hr.other.subsidies', 'other_subsidies_detail', self.name.id,
                                                     'other_subsidies_state')
        return self.other_subsidies

    # 扣款金额 扣款金额申请通过后获取扣款金额
    def get_deduction(self):
        self.deduction = self._get_field_value('tx.hr.withhold', 'withhold_detail', self.name.id, 'withhold_state')
        return self.deduction

    # 工龄工资 住房补贴 元老补助 岗位津贴 社保
    def get_wage(self):
        contracts = self.env['hr.contract'].search([('employee_id', '=', self.name.id)])
        for contract in contracts:  # 修改代码，用循环处理返回多个记录
            self.seniority_pay = contract.seniority_wage
            self.housing_subsidy = contract.housing_subsidy
            self.senior_allowance = contract.senior_allowance
            self.job_subsidy = contract.job_subsidy
            self.social_security = contract.social_security.money
        return self.seniority_pay, self.housing_subsidy, self.senior_allowance, self.job_subsidy, self.social_security

    # 基本工资=基本工资/应出勤天数*实际出勤天数
    # 岗位工资=岗位工资/应出勤天数*实际出勤天数
    def payroll_computation(self, days_of_attendance_due, attendance):
        contracts = self.env['hr.contract'].search([('employee_id', '=', self.name.id)])
        for contract in contracts:
            wage = contract.wage * attendance / days_of_attendance_due
            post_wage = contract.post_wage * attendance / days_of_attendance_due
            if self.attendance < 15:
                self.housing_subsidy = 0
            self.wage = wage
            self.post_wage = post_wage
        return self.wage, self.post_wage, self.housing_subsidy

    # 绩效工资=绩效工资*绩效系数
    def merit_pay_calculation(self, performance_coefficient):
        contracts = self.env['hr.contract'].search([('employee_id', '=', self.name.id)])
        for contract in contracts:
            merit_pay = contract.performance_pay * performance_coefficient
            self.merit_pay = merit_pay
        return self.merit_pay

    # 正常加班工资 = 加班时长*15
    def get_regular_overtime_pay(self, normal_overtime_hours, regular_overtime_rite):
        self.regular_overtime_pay = normal_overtime_hours * regular_overtime_rite
        return self.regular_overtime_pay

    # 节假加班工资
    def get_holiday_overtime_pay(self, holiday_overtime_hours, holiday_overtime_rite):
        self.holiday_overtime_pay = holiday_overtime_hours * holiday_overtime_rite
        return self.holiday_overtime_pay

    # 基本工资 和 计件工资比较计算工资总额
    def get_total_wage_bill(self, wage, post_wage, merit_pay, piece_rate, seniority_pay,
                            regular_overtime_pay, holiday_overtime_pay, attendance_bonus,
                            other_subsidies, senior_allowance, job_subsidy, housing_subsidy):
        salary_floor = max(wage + post_wage + merit_pay, piece_rate)
        salary = salary_floor + seniority_pay + regular_overtime_pay + holiday_overtime_pay + attendance_bonus + other_subsidies + senior_allowance + job_subsidy + housing_subsidy
        self.total_wage_bill = salary
        return self.total_wage_bill

    # 应付工资 工资总额-扣款金额
    def get_wages_payable(self, total_wage_bill, deduction):
        self.wages_payable = total_wage_bill - deduction
        return self.wages_payable

    # 计算个税
    def get_individual_income_tax(self, social_security):
        sum_wages_payable = 0
        mont = 0
        wages = self.env['tx.hr.salary.calculation'].search([('year', '=', self.year), ('name', '=', self.name.id)])
        if wages:
            sum_wages_payable = sum(wages.mapped('wages_payable'))
            mont = len(wages)

        individual_income_sum = self.env['tx.hr.individual_income_tax'].search(
            [('name', '=', self.name.id)]).individual_income_sum
        individual_income_tax = sum_wages_payable - social_security * mont - individual_income_sum * mont - 5000

        tax_rates = [0.03, 0.1, 0.2, 0.25, 0.30, 0.35, 0.45]
        income_thresholds = [0, 36000, 144000, 300000, 420000, 660000, 960000]
        tax = 0
        for rate, threshold in zip(tax_rates, income_thresholds):
            if individual_income_tax > threshold:
                tax = individual_income_tax * rate

        self.individual_income_tax = tax if tax > 0 else 0
        return self.individual_income_tax

    # 实付工资 应付工资-社保-个税
    def calculate_net_pay(self, wages_payable, social_security, individual_income_tax):
        self.net_pay = wages_payable - social_security - individual_income_tax

    # 初始化插入数据
    @api.model
    def init(self):
        if not self.search([], limit=1):
            employees = self.env['hr.employee'].sudo().search([])
            self.with_context(skip_constraints=True).create([{'name': employee.id} for employee in employees])

    # 相同员工同一年月数据约束
    @api.constrains('name', 'month', 'year')
    def repeat_monitoring(self):
        if not self.env.context.get('skip_constraints'):
            domain = [
                ('name', '=', self.name.id),
                ('year', '=', self.year),
                ('month', '=', self.month),
                ('id', '!=', self.id),
            ]
            if self.search_count(domain) > 0:
                raise ValidationError('员工 "%s" %s 年 %s 月已有记录' % (self.name.name, self.year, self.month))

    # 更新数据
    def refresh_data(self):
        time_now = datetime.datetime.now().today()
        existing_calculation = self.env['tx.hr.salary.calculation'].search([
            ('name', 'in', self.env['hr.employee'].ids),
            ('month', '=', str(time_now.month)),
            ('year', '=', str(time_now.year))
        ])
        missing_employees = self.env['hr.employee'].browse(
            set(self.env['hr.employee'].ids) - set(existing_calculation.mapped('name.id')))
        new_calculation = missing_employees.mapped(lambda employee: {
            'name': employee.id,
            'month': str(time_now.month),
            'year': str(time_now.year)
        })
        self.env['tx.hr.salary.calculation'].create(new_calculation)
        self.run_main()


class PieceworkType(models.Model):
    _name = "tx.hr.social.security"
    name = fields.Char("社保类型")
    money = fields.Float("社保金额")
