from odoo import fields, models, api
from datetime import datetime, timedelta, date
from dateutil import relativedelta
import holidays
from dateutil.rrule import rrule, WEEKLY, SU
import calendar

from odoo.exceptions import ValidationError


class TxHrHolidayType(models.Model):
    _name = "tx.hr.holiday.type"
    _description = '假日类型'

    name = fields.Char(string="名称")

    def init(self):
        # 删除所有记录
        self.env['tx.hr.holiday.type'].sudo().search([]).unlink()

        self.create([{'name': '节假日'}, {'name': '休息日'}, {'name': '调休'}])


class HolidayCalculation(models.Model):
    _name = 'tx.hr.holiday.calculation'
    year = fields.Selection(
        [(str(year), str(year) + '年') for year in range(datetime.now().year, datetime.now().year + 13)],
        string='年份'
    )
    month = fields.Selection(
        [(str(month), str(month) + '月') for month in range(1, 13)],
        string='月份'
    )
    day = fields.Char(string='日', readonly=True)
    # state = fields.Selection([('sunday', '休息日'), ('holiday', '节假日'), ('other', '其他')], string="是否放假", default=False)
    date = fields.Date(string='日期', required=True)
    holiday_id = fields.Many2one('tx.hr.holiday.type', ondelete='cascade', string='假日类型', required=True)
    remark = fields.Text(string="备注")

    @api.model
    def init(self):
        # 删除所有记录
        self.env['tx.hr.holiday.calculation'].sudo().search([]).with_context(skip_constraints=True).unlink()

        year = datetime.now().year
        self._create_or_update_holidays(year)

    def next_year(self):
        year = datetime.now().year + 1
        self._create_or_update_holidays(year)

    def _create_or_update_holidays(self, year):
        cn_holidays = holidays.CountryHoliday('CN', years=[year])  # 创建中国法定节假日对象
        # holiday_dates = list(cn_holidays.keys())

        # 获取 cn_holidays 的所有键
        cn_holidays_keys = cn_holidays.keys()

        # 列表，包含要创建的记录的值列表
        records_to_create = []
        new_holiday = None

        # 检查是否已存在名为 "节假日" 的 holiday_id
        existing_holiday = self.env['tx.hr.holiday.type'].search([('name', '=', '节假日')], limit=1)

        if not existing_holiday:
            # 不存在时创建新的 holiday_id
            new_holiday = self.env['tx.hr.holiday.type'].create({'name': '节假日'})
        else:
            new_holiday = existing_holiday

        for holiday_date in cn_holidays_keys:
            record_values = {
                'year': str(year),
                'month': str(holiday_date.month),
                'date': holiday_date,
                'holiday_id': new_holiday.id,
            }
            records_to_create.append(record_values)

        # 获取一年中所有的周日日期
        start_date = date(year, 1, 1)
        end_date = date(year, 12, 31)
        sundays = list(rrule(WEEKLY, dtstart=start_date, until=end_date, byweekday=SU))

        # 检查是否已存在名为 "节假日" 的 holiday_id
        existing_holiday = self.env['tx.hr.holiday.type'].search([('name', '=', '休息日')], limit=1)

        if not existing_holiday:
            # 不存在时创建新的 holiday_id
            new_holiday = self.env['tx.hr.holiday.type'].create({'name': '休息日'})
        else:
            new_holiday = existing_holiday

        for sunday in sundays:
            sunday = sunday.date()
            if sunday not in cn_holidays_keys:
                record_values = {
                    'year': str(year),
                    'month': str(sunday.month),
                    'date': sunday,
                    'holiday_id': new_holiday.id,
                }
                records_to_create.append(record_values)

        self.with_context(skip_constraints=True).create(records_to_create)
        # self.create(records_to_create)

    _sql_constraints = [
        ('date_uniq', 'unique (date)', "不要重复定义 !"),
    ]

    @api.model
    def create(self, vals):
        if not self.env.context.get('skip_constraints'):
            date_obj = datetime.strptime(vals['date'], '%Y-%m-%d')
            year = date_obj.year
            month = date_obj.month

            schedulings = self.env["tx.hr.scheduling"].search([('year', '=', year), ('month', '=', month)])
            if schedulings:
                days_of_attendance_due = schedulings[1].days_of_attendance_due
                schedulings.write({'days_of_attendance_due': days_of_attendance_due - 1})

        return super(HolidayCalculation, self).create(vals)

    def unlink(self):
        if not self.env.context.get('skip_constraints'):
            schedulings = self.env["tx.hr.scheduling"].search([('year', '=', self.date.year), ('month', '=', self.date.month)])
            if schedulings:
                days_of_attendance_due = schedulings[1].days_of_attendance_due
                schedulings.write({'days_of_attendance_due': days_of_attendance_due + 1})

        super(HolidayCalculation, self).unlink()

    def name_get(self):
        result = []
        for record in self:
            name = record.holiday_id.name
            result.append((record.id, name))
        return result

    # def create_or_update_holiday(self, year, month, day, state):
    #     record = self.search([('year', '=', year), ('month', '=', month), ('day', '=', day)], limit=1)
    #     if record:
    #         record.with_context(skip_constraints=True).write({'state': state})
    #     else:
    #         values = {
    #             'year': str(year),
    #             'month': str(month),
    #             'day': str(day),
    #             'state': state
    #         }
    #         self.with_context(skip_constraints=True).create(values)

    # @api.constrains('state')
    # def change_days_attendance_due(self):
    #     if not self.env.context.get('skip_constraints'):
    #         scheduling = self.env["tx.hr.scheduling"].search([('year', '=', self.year)])
    #         if scheduling:
    #             for schedule in scheduling:
    #                 schedule.days_of_attendance_due += 1 if self.state == '1' else -1


class Scheduling(models.Model):
    _name = "tx.hr.scheduling"
    _description = "排班"

    name = fields.Many2one('hr.employee', string="员工", required=True)
    department_id = fields.Many2one('hr.department', string="部门", related='name.department_id', store=True)
    job_id = fields.Many2one('hr.job', string='职位', related='name.job_id', readonly=True)
    classes = fields.Many2one('tx.hr.classes', string="班次")
    year = fields.Char(string='年份', readonly=True, default=str(datetime.now().year))
    month = fields.Selection(
        [(str(month), str(month) + '月') for month in range(1, 13)],
        string='月份',
        required=True,
        default=str(datetime.now().month))
    remark = fields.Text(string="备注")
    days_of_attendance_due = fields.Integer(string='应出勤天数', compute='_compute_days_of_attendance_due', store=True)
    active = fields.Boolean(default=True)

    def production_post(self):
        return {
            "name": "员工明细",
            "type": "ir.actions.act_window",
            "res_model": 'tx.hr.classes',
            "view_mode": "tree",
            "views": [(self.env.ref('tx_hr.tx_hr_classes_tree').id, "tree")],
            "target": "new",
        }
        # context = self.env.context
        # my_parameter_value = context.get('my_parameter')
        # self.classes = my_parameter_value

    def update_data(self):
        for item in self.env['tx.hr.scheduling'].search([]):
            item.active = False
            if item.month != str(datetime.now().month):
                item.create({
                    'name': item.name.id,
                    'month': str(datetime.now().month+1),
                    'classes': item.classes.id,
                    'active': True,
                })

    def update_employee(self):
        employees = self.env['hr.employee'].sudo().search([])

        for employee in employees:
            if not self.env['tx.hr.scheduling'].search([('name', '=', employee.id)]):
                self.create({
                    'name': employee.id,
                })

    @api.depends('year', 'month')
    def _compute_days_of_attendance_due(self):
        for item in self:
            record = self.env['tx.hr.holiday.calculation'].sudo().search(
                [('year', '=', item.year), ('month', '=', item.month)])
            if record:
                item.days_of_attendance_due = calendar.monthrange(int(item.year), int(item.month))[1] - len(record)

    @api.model
    def init(self):
        if not self.search([], limit=1):
            employees = self.env['hr.employee'].sudo().search([])
            if employees:
                for employee in employees:
                    self.create({
                        'name': employee.id,
                    })


class TxHrClasses(models.Model):
    _name = "tx.hr.classes"
    _description = '班次表'

    name = fields.Char(string="名称")
    start_time1 = fields.Float(string="早上上班时间（h）")
    end_time1 = fields.Float(string="早上下班时间（h）")
    start_time2 = fields.Float(string="下午上班时间（h）")
    end_time2 = fields.Float(string="下午下班时间（h）")
    start_time3 = fields.Float(string="加班上班时间1（h）")
    end_time3 = fields.Float(string="加班下班时间1（h）")
    start_time4 = fields.Float(string="加班上班时间2（h）")
    end_time4 = fields.Float(string="加班下班时间2（h）")

    # 上班时间约束
    @api.constrains('start_time1', 'end_time1', 'start_time2', 'end_time2', 'start_time3', 'end_time3', 'start_time4', )
    def _check_time(self):
        if self.start_time1 > self.end_time1:
            raise ValidationError('早上上班时间不能大于下班时间')
        if self.start_time2 > self.end_time2:
            raise ValidationError('下午上班时间不能大于下班时间')
