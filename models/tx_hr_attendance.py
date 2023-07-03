# -*- coding: utf-8 -*-

from odoo import models, fields, api
from datetime import datetime, timedelta, time


class Attendance(models.Model):
    _name = 'tx.hr.attendance'
    _description = '考勤'

    pin = fields.Char(string='工号')
    name = fields.Char(string='姓名')
    clock_in_time = fields.Datetime(string='打卡时间')
    weekday = fields.Char(string='星期')
    adjusted_clock_in_time = fields.Datetime(string='Adjusted Clock In Time', compute='_compute_adjusted_clock_in_time'
                                             , store=True)

    @api.depends('clock_in_time')
    def _compute_adjusted_clock_in_time(self):
        for record in self:
            if record.clock_in_time:
                record.adjusted_clock_in_time = record.clock_in_time + timedelta(hours=8)
            else:
                record.adjusted_clock_in_time = False

    @api.constrains('clock_in_time')
    def check_in(self):
        weekday_names = ['星期一', '星期二', '星期三', '星期四', '星期五', '星期六', '星期日']
        employee = self.env['hr.employee'].search([('pin', '=', self.pin)], limit=1)

        if not employee:
            return

        self.weekday = weekday_names[(self.clock_in_time + timedelta(hours=8)).weekday()]
        self.name = employee.name


class AttendanceDaily(models.Model):
    """
    考勤日报
    """
    _name = 'tx.hr.attendance.daily'
    _description = '考勤日报'

    employee_id = fields.Many2one('hr.employee', string='员工', readonly=True)
    department_id = fields.Many2one('hr.department', string='部门', related='employee_id.department_id', readonly=True, store=True)
    employee_job_id = fields.Many2one('hr.job', string='职位', related='employee_id.job_id', readonly=True)
    pin = fields.Char(string='工号')
    attendance_time = fields.Float(string='上班时间(天)', digits=(2, 1), default=0)
    normal_overtime_hours = fields.Float(string='正常加班时间(H)', digits=(3, 1), default=0)
    holiday_overtime_hours = fields.Float(string='节假日加班时间(H)', digits=(3, 1), default=0)
    date = fields.Date(string='日期')
    year = fields.Integer(string='年')
    month = fields.Integer(string='月')
    punch_in_morning = fields.Char(string='早上上班打卡')
    clock_out_morning = fields.Char(string='早上下班打卡')
    punch_in_afternoon = fields.Char(string='下午上上班打卡')
    clock_out_afternoon = fields.Char(string='下午下班打卡')
    punch_in_evening = fields.Char(string='晚上上班打卡')
    clock_out_evening = fields.Char(string='晚上下班打卡')
    # punch_in_night = fields.Datetime(string='深夜上班打卡')
    # clock_out_night = fields.Datetime(string='深夜下班打卡')
    late_leave_early = fields.Integer(string='迟到早退', default=0)
    clock_in_time = fields.Datetime()

    # 保存考勤记录
    @api.model
    def clock_in(self, values):
        pin = values[0]
        # pin = self.env.context.get('pin')
        clock_in_date = datetime.strptime(values[1], '%Y-%m-%d %H:%M:%S')
        # clock_in_date = datetime.strptime(self.env.context.get('clock_in_time'), '%Y-%m-%d %H:%M:%S') + timedelta(
        #     hours=8)
        date = clock_in_date.date()
        clock_in_time = clock_in_date.time()

        employee = self.env['hr.employee'].search([('pin', '=', pin)], limit=1)
        if not employee:
            return

        # 查询该员工当天是否有打卡记录
        record = self.search([('employee_id', '=', employee.id), ('date', '=', clock_in_date.date())], limit=1)

        # 班次
        classes = self.get_classes(employee).classes
        if not classes:
            return
        morning_in_time = tarn_time(classes.start_time1, date)
        morning_out_time = tarn_time(classes.end_time1, date)
        afternoon_in_time = tarn_time(classes.start_time2, date)
        afternoon_out_time = tarn_time(classes.end_time2, date)
        evening_in_time = tarn_time(classes.start_time3, date)
        evening_out_time = tarn_time(classes.end_time3, date)
        night_in_time = tarn_time(classes.start_time4, date)
        night_out_time = tarn_time(classes.end_time4, date)

        delta = timedelta(hours=1)

        # 月报记录
        emp_month_attendance = self.env['tx.hr.attendance.monthly'].search([('year', '=', clock_in_date.date().year),
                                                                            ('month', '=', clock_in_date.date().month),
                                                                            ('employee.id', '=', employee.id)])

        # 更新月报数据
        add_temp = {
            'late_leave_early_add': 0,
            'attendance_time_add': 0,
            'normal_overtime_hours_add': 0,
            'holiday_overtime_hours_add': 0
        }

        # 是否出差
        business = self.env['tx.hr.business.trip'].search(
            [('business_person_ids', 'in', self.env.user.employee_ids.ids),
             ('begin_time', '<=', date),
             ('over_time', '>=', date)], limit=1)
        is_business = business.business_state == 'approved'

        # 是否节假日
        schedule = self.env['tx.hr.holiday.calculation'].search([('date', '=', date)])

        domain = [
            ('overtime_person_ids', 'in', self.env.user.employee_ids.ids),
            ('start_time', '>=', date.strftime('%Y-%m-%d 00:00:00')),
            ('end_time', '<=', date.strftime('%Y-%m-%d 23:59:59')),
        ]
        overtime_order = self.env["tx.hr.overtime"].sudo().search(domain, limit=1)
        order = {}
        # 休息日但是没有申请单
        if schedule and (not overtime_order or overtime_order.state != 'approved'):
            return
        elif overtime_order:
            order['start_time'] = overtime_order['start_time'] + timedelta(hours=8)
            order['end_time'] = overtime_order['end_time'] + timedelta(hours=8)
        holiday = {
            'is_holiday': schedule and overtime_order and overtime_order.state == 'approved',
            'is_overtime': overtime_order and overtime_order.state == 'approved',
            'overtime_order': order,
            'is_business': is_business
        }

        # 如果有打卡记录，就更新记录
        if record:
            # 判断打卡时间段
            if clock_in_date <= morning_out_time:
                if not record.punch_in_morning:
                    record.punch_in_morning = clock_in_time
                    record.late_leave_early += late_leave_early_total(clock_in_date, morning_in_time, 1, add_temp, holiday)
                elif not record.clock_out_morning and clock_in_date >= morning_out_time - delta:
                    record.clock_out_morning = clock_in_time
                    attendance_time_total(record, 'morning', classes, date, add_temp, holiday)
                    record.late_leave_early += late_leave_early_total(clock_in_date, morning_out_time, 0, add_temp,
                                                                      holiday)
            elif clock_in_date <= afternoon_in_time:
                if not record.punch_in_afternoon:
                    record.punch_in_afternoon = clock_in_time
                    attendance_time_total(record, 'morning', classes, date, add_temp, holiday)
                if not record.clock_out_morning:
                    record.clock_out_morning = clock_in_time
                    attendance_time_total(record, 'morning', classes, date, add_temp, holiday)
            elif clock_in_date <= afternoon_out_time:
                if not record.punch_in_afternoon:
                    record.punch_in_afternoon = clock_in_time
                    attendance_time_total(record, 'morning', classes, date, add_temp, holiday)
                    record.late_leave_early += late_leave_early_total(clock_in_date, afternoon_in_time, 1, add_temp,
                                                                      holiday)
                elif not record.clock_out_afternoon and clock_in_date >= afternoon_out_time - delta:
                    record.clock_out_afternoon = clock_in_time
                    attendance_time_total(record, 'afternoon', classes, date, add_temp, holiday)
                    record.late_leave_early += late_leave_early_total(clock_in_date, afternoon_out_time, 0, add_temp,
                                                                      holiday)
            elif clock_in_date <= evening_in_time:
                if not record.clock_out_afternoon:
                    record.clock_out_afternoon = clock_in_time
                    attendance_time_total(record, 'afternoon', classes, date, add_temp, holiday)
                elif not record.punch_in_evening:
                    record.punch_in_evening = clock_in_time
                    self.overtime_total(record, classes, True, add_temp, holiday)
            else:
                if not record.punch_in_evening:
                    record.punch_in_evening = clock_in_time
                    self.overtime_total(record, classes, True, add_temp, holiday)
                else:
                    record.clock_out_evening = clock_in_time
                    self.overtime_total(record, classes, False, add_temp, holiday)

            if is_business:
                return
            emp_month_attendance.write(
                {'late_leave_early': emp_month_attendance.late_leave_early + add_temp['late_leave_early_add'],
                 'attendance_time': emp_month_attendance.attendance_time + add_temp['attendance_time_add'],
                 'normal_overtime_hours': emp_month_attendance.normal_overtime_hours
                                          + add_temp['normal_overtime_hours_add'],
                 'holiday_overtime_hours': emp_month_attendance.holiday_overtime_hours
                                           + add_temp['holiday_overtime_hours_add']})

            return self.write(record)

        # 如果没有打卡记录，就创建一条新记录
        else:
            attend_record = {
                'employee_id': employee.id,
                'pin': pin,
                'date': clock_in_date.date(),
                'year': clock_in_date.date().year,
                'month': clock_in_date.date().month,
                'late_leave_early': 0
            }

            if clock_in_date <= morning_out_time:
                attend_record['punch_in_morning'] = clock_in_time
                attend_record['late_leave_early'] += late_leave_early_total(clock_in_date, morning_in_time, 1, add_temp,
                                                                            holiday)
            elif clock_in_date <= afternoon_in_time:
                attend_record['clock_out_morning'] = clock_in_time
                attend_record['punch_in_afternoon'] = clock_in_time
            elif clock_in_date <= afternoon_out_time:
                attend_record['punch_in_afternoon'] = clock_in_time
                attend_record['late_leave_early'] += late_leave_early_total(clock_in_date, morning_in_time, 1, add_temp,
                                                                            holiday)
            elif clock_in_date <= evening_in_time:
                attend_record['punch_in_evening'] = clock_in_time
            elif clock_in_date <= night_out_time:
                attend_record['punch_in_evening'] = clock_in_time
            else:
                attend_record['clock_out_evening'] = clock_in_time

            if is_business:
                return

            # 新增月报
            if not emp_month_attendance:
                emp_month_attendance_record = {
                    'employee': employee.id,
                    'pin': pin,
                    'year': clock_in_date.date().year,
                    'month': clock_in_date.date().month,
                    'late_leave_early': attend_record['late_leave_early']
                }
                self.env['tx.hr.attendance.monthly'].create(emp_month_attendance_record)
            else:
                emp_month_attendance.write(
                    {'late_leave_early': emp_month_attendance.late_leave_early + add_temp['late_leave_early_add']})

            return self.create(attend_record)

    # 获取班次
    def get_classes(self, employee):
        date = fields.Date.today()
        return self.env["tx.hr.scheduling"].sudo().search(
            [('name', '=', employee.id), ('year', '=', date.year), ('month', '=', date.month)],
            limit=1)

    # 加班记录
    def overtime_total(self, record, classes, is_first, add_temp, holiday):
        if holiday['is_business']:
            return
        date = record.date
        punch_in_evening = None
        clock_out_evening = None
        start_time3 = tarn_time(classes.start_time3, date)

        if record.clock_out_evening:
            punch_in_evening = my_strptime(date, record.punch_in_evening)
            clock_out_evening = my_strptime(date, record.clock_out_evening)
        else:
            clock_out_evening = my_strptime(date, record.punch_in_evening)
            punch_in_evening = clock_out_evening.replace(hour=0, minute=0, second=0)

        if is_first and not record.clock_out_afternoon:
            record.clock_out_afternoon = clock_out_evening.time()
            attendance_time_total(record, "afternoon", classes, date, add_temp, holiday)
            record.clock_out_afternoon = None

        overtime_order = holiday['overtime_order']
        # 节假日
        if holiday['is_holiday']:
            if clock_out_evening <= overtime_order.start_time or punch_in_evening >= overtime_order.end_time:
                return
            start = max(overtime_order.start_time, punch_in_evening, start_time3)
            end = min(overtime_order.end_time, clock_out_evening)

            temp_holiday = record.holiday_overtime_hours
            record.holiday_overtime_hours = (end - start).total_seconds() / 3600
            add_temp['holiday_overtime_hours_add'] = record.holiday_overtime_hours - temp_holiday
            return

        if holiday['is_overtime']:
            if overtime_order.end_time <= start_time3:
                return
            start_time = max(overtime_order.start_time, punch_in_evening, start_time3)
            end_time = min(overtime_order.end_time, clock_out_evening)
            start_time4 = tarn_time(classes.start_time4, date)
            end_time3 = tarn_time(classes.end_time3, date)
            # 深夜加班
            if start_time >= start_time4:
                temp = record.holiday_overtime_hours
                record.holiday_overtime_hours = (end_time - start_time).total_seconds() / 3600
                add_temp['holiday_overtime_hours_add'] = record.holiday_overtime_hours - temp
            elif end_time <= end_time3:
                temp = record.normal_overtime_hours
                record.normal_overtime_hours = (end_time - start_time).total_seconds() / 3600
                add_temp['normal_overtime_hours_add'] = record.normal_overtime_hours - temp
            else:
                temp_normal = record.normal_overtime_hours
                temp_holiday = record.holiday_overtime_hours
                record.normal_overtime_hours = (end_time3 - start_time).total_seconds() / 3600
                record.holiday_overtime_hours = (end_time - start_time4).total_seconds() / 3600
                add_temp['normal_overtime_hours_add'] = record.normal_overtime_hours - temp_normal
                add_temp['holiday_overtime_hours_add'] = record.holiday_overtime_hours - temp_holiday


# 迟到早退记录
def late_leave_early_total(clock_in_time, time_period, work_type, add_temp, holiday):
    if holiday['is_holiday'] or holiday['is_business']:
        add_temp['late_leave_early_add'] = 0
        return 0
    out_time = time_period + timedelta(minutes=3) if work_type else time_period - timedelta(minutes=3)
    if (work_type and clock_in_time > out_time) or (not work_type and clock_in_time < out_time):
        add_temp['late_leave_early_add'] = 1
        return 1
    else:
        add_temp['late_leave_early_add'] = 0
        return 0


def attendance_time_total(record, working_time, classes, date, add_temp, holiday):
    """
    计算上班时间
    :param record: 日报记录
    :param working_time: 打卡时间
    :param classes: 班次
    """
    if holiday['is_business']:
        return
    start = 0
    end = 0
    noon_break = 0
    # 获取排班
    morning_in_time = tarn_time(classes.start_time1, date)
    morning_out_time = tarn_time(classes.end_time1, date)
    afternoon_in_time = tarn_time(classes.start_time2, date)
    afternoon_out_time = tarn_time(classes.end_time2, date)

    # 计算工作时长
    work_duration = (morning_out_time - morning_in_time) + (afternoon_out_time - afternoon_in_time)
    normal_work_minutes = work_duration.total_seconds() // 60

    if working_time == 'morning' and record.punch_in_morning:
        if record.clock_out_morning and record.punch_in_afternoon:
            return
        punch_in_morning = my_strptime(date, record.punch_in_morning)
        # 判断下午上班卡还是早上下班卡
        clock_out_morning = my_strptime(date, record.clock_out_morning) \
            if record.clock_out_morning \
            else my_strptime(date, record.punch_in_afternoon)
        start = max(punch_in_morning, morning_in_time)
        end = min(clock_out_morning, morning_out_time)
        # 节假日
        if holiday['is_holiday']:
            overtime_order = holiday['overtime_order']
            if clock_out_morning <= overtime_order.start_time or punch_in_morning >= overtime_order.end_time:
                return
            start = max(start, overtime_order.start_time)
            end = min(end, overtime_order.end_time)
    # 早上打了下班卡或者下午上班卡
    elif record.clock_out_morning or record.punch_in_afternoon:
        punch_in_afternoon = None
        if record.punch_in_afternoon:
            punch_in_afternoon = my_strptime(date, record.punch_in_afternoon)
        else:
            punch_in_afternoon = afternoon_in_time

        clock_out_afternoon = my_strptime(date, record.clock_out_afternoon)
        start = max(punch_in_afternoon, afternoon_in_time)
        end = min(clock_out_afternoon, afternoon_out_time)
        # 节假日
        if holiday['is_holiday']:
            overtime_order = holiday['overtime_order']
            if clock_out_afternoon <= overtime_order.start_time or punch_in_afternoon >= overtime_order.end_time:
                return
            start = max(start, overtime_order.start_time)
            end = min(end, overtime_order.end_time)
    elif record.punch_in_morning:
        # 只打了早上上班和下午下班
        punch_in_morning = my_strptime(date, record.punch_in_morning)
        clock_out_afternoon = my_strptime(date, record.clock_out_afternoon)
        start = max(punch_in_morning, morning_in_time)
        end = min(clock_out_afternoon, afternoon_out_time)

        # 节假日
        if holiday['is_holiday']:
            overtime_order = holiday['overtime_order']
            if clock_out_afternoon <= overtime_order.start_time or start >= overtime_order.end_time:
                return
            start = max(start, overtime_order.start_time)
            end = min(end, overtime_order.end_time)

            end -= afternoon_in_time - morning_out_time
    else:
        return

    if holiday['is_holiday']:
        add_time = (end - start).total_seconds() / 3600
        record.holiday_overtime_hours += add_time
        add_temp['holiday_overtime_hours_add'] = add_time
    else:
        add_time = (end - start).total_seconds() / 60 / normal_work_minutes
        record.attendance_time += add_time
        add_temp['attendance_time_add'] = add_time


def my_strptime(date, clock_time):
    return datetime.strptime(str(date) + " " + clock_time, '%Y-%m-%d %H:%M:%S')


def tarn_time(work_time, date):
    """
        日期转换
    """
    # 将浮点数转换为小时和分钟
    hours = int(work_time)
    minutes = int((work_time % 1) * 60)

    if work_time:
        time_obj = time(hours, minutes)
        datetime_obj = datetime.combine(date, time_obj)
        return datetime_obj


# 定义正常打卡时间
normal_times = ["08:00", "12:00", "14:00", "18:00"]


class AttendanceMonthly(models.Model):
    """
    考勤月报
    """
    _name = "tx.hr.attendance.monthly"
    _description = "考勤月报"

    year = fields.Char(string='年')
    month = fields.Char(string='月')
    employee = fields.Many2one('hr.employee', string='员工')
    pin = fields.Char(string='工号')
    department_id = fields.Many2one('hr.department', string='部门', related='employee.department_id', readonly=True, store=True)
    employee_job_id = fields.Many2one('hr.job', string='职位', related='employee.job_id', readonly=True)
    late_leave_early = fields.Integer(string='迟到早退', default=0)
    attendance_time = fields.Float(string='上班时间(天)', digits=(2, 1), default=0)
    normal_overtime_hours = fields.Float(string='正常加班时间(H)', digits=(3, 1), default=0)
    holiday_overtime_hours = fields.Float(string='节假日加班时间(H)', digits=(3, 1), default=0)
