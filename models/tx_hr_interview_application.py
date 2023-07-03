from datetime import datetime
from odoo.exceptions import ValidationError
from odoo import fields, models, api
import re


class TxHrInterviewApplication(models.Model):
    _name = 'tx.hr.interview.application'
    _description = 'Interview Application'

    department = fields.Many2one('hr.department', string='应聘部门')
    position = fields.Many2one('hr.job', string='应聘职位')
    date = fields.Date(string='应聘日期', default=fields.Date.today())
    name = fields.Char(string='姓名', required=True)
    gender = fields.Selection([
        ('male', '男'),
        ('female', '女'),
        ('other', '未知')
    ], string='性别', required=True)
    native_place = fields.Char(string='籍贯', required=True)
    nation = fields.Char(string='民族', required=True)
    birth = fields.Date(string='出生日期', required=True)
    marital_status = fields.Selection([
        ('single', '未婚'),
        ('married', '已婚'),
        ('divorced', '离异')
    ], string='婚姻状况', required=True)
    education = fields.Selection([
        ('middle_school', '初中'),
        ('high_school', '高中'),
        ('college', '大专'),
        ('bachelor', '本科'),
        ('master', '硕士'),
        ('phd', '博士'),
        ('other', '其他')
    ], string='学历', required=True)
    political_outlook = fields.Selection([
        ('member', '团员'),
        ('party_member', '党员'),
        ('the_masses', '群众'),
        ('other', '其他'),
    ], string='政治面貌')
    id_number = fields.Char(string='身份证号码', required=True)
    computer_skills = fields.Selection([
        ('basic', '基础'),
        ('intermediate', '中级'),
        ('advanced', '高级')
    ], string='电脑水平')
    household_register = fields.Char(string='户口所在地', required=True)
    language_skills = fields.Selection([
        ('basic', '基础'),
        ('intermediate', '中级'),
        ('advanced', '高级')
    ], string='外语水平')
    current_address = fields.Char(string='现住地址', required=True)
    employment_status = fields.Selection([
        ('employed', '在职'),
        ('unemployed', '无业')
    ], string='在职情况', required=True)
    availability = fields.Date(string='能到岗时间', required=True)
    contact_number = fields.Char(string='联系电话', required=True)
    emergency_contact = fields.Char(string='紧急联系人/电话', required=True)
    expected_salary = fields.Float(string='期望薪资', required=True)
    health_condition = fields.Selection([
        ('healthy', '健康'),
        ('unhealthy', '不健康')
    ], string='个人健康状况', required=True)
    disease = fields.Char(string='重要疾病')
    driving_license = fields.Boolean(string='驾照')
    driving_license_style = fields.Char(string='驾照类型')
    maternity_status = fields.Selection([
        ('no', '否'),
        ('pregnancy', '孕期'),
        ('childbirth', '产期'),
        ('breastfeeding', '哺乳期')
    ], string='是否属于三期')
    recruitment_channel = fields.Selection([
        ('company_website', '公司网站'),
        ('job_portal', '招聘网站'),
        ('friend_referral', '朋友介绍'),
        ('other', '其他途径')
    ], string='招聘信息来源')
    health_issues = fields.Char(string='重要疾病')
    education_id = fields.One2many('tx.hr.education', 'interview_id', string='教育状况')
    work_experience = fields.One2many('tx.hr.work.experience', 'interview_id', string='工作简历')
    family_member = fields.One2many('tx.hr.family.member', 'interview_id', string='主要社会关系（家庭成员）')


class TxHrEducation(models.Model):
    _name = 'tx.hr.education'
    _description = 'Education'

    interview_id = fields.Many2one('tx.hr.interview.application')
    start_date = fields.Date(string='Start Date')
    end_date = fields.Date(string='End Date')
    school = fields.Char(string='School')
    major = fields.Char(string='Major')
    degree = fields.Selection([
        ('high', '高中'),
        ('regularCollegeCourse', '本科'),
        ('master', '硕士'),
        ('phd', '博士'),
        ('other', '其他'),
    ], string='Degree')
    study_mode = fields.Selection([
        ('full_time', '全日制'),
        ('part_time', '非全日制')
    ], string='Study Mode')


class TxHrWorkExperience(models.Model):
    _name = 'tx.hr.work.experience'
    _description = 'Work Experience'

    interview_id = fields.Many2one('tx.hr.interview.application')
    start_date = fields.Date(string='开始日期')
    end_date = fields.Date(string='结束日期')
    company_name = fields.Char(string='公司名称')
    position = fields.Char(string='地点')
    salary = fields.Float(string='工资', widget='monetary')
    reason_for_leaving = fields.Text(string='离职原因')
    reference_person = fields.Char(string='证明人及电话')


class TxHrFamilyMember(models.Model):
    _name = 'tx.hr.family.member'
    _description = 'Family Member'

    interview_id = fields.Many2one('tx.hr.interview.application')
    name = fields.Char(string='Name')
    relationship = fields.Char(string='Relationship')
    employer = fields.Char(string='Employer')
    contact_number = fields.Char(string='Contact Number')


