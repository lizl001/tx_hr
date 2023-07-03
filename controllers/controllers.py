# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request
from datetime import datetime, timedelta
import logging

_logger = logging.getLogger(__name__)


class AttendanceController(http.Controller):
    @http.route("/iclock/cdata/", type="http", auth="none", csrf=False)
    def iclock_cdata(self, **kw):
        if request.httprequest.method == 'GET':
            # 公司
            # result = "GET OPTION FROM: CJ9G221560058\nErrorDelay=30\nDelay=60\nTransInterval=0\nTransFlag=100000000000\nTimeZone=8\nRealtime=1"
            # luoliq
            result = "GET OPTION FROM: CJ9G232060312\nErrorDelay=30\nDelay=60\nTransInterval=0\nTransFlag=100000000000\nTimeZone=8\nRealtime=1"
            return result
        if request.httprequest.method == 'POST':
            attendance_models = request.env['tx.hr.attendance']
            attendance_record = request.env['tx.hr.attendance.daily']
            _logger.info("--------------" + kw.get('table'))
            if kw.get('table') == 'ATTLOG':
                data = request.httprequest.data.decode()
                temp_list = data.split('\t')
                try:
                    if temp_list[0] and temp_list[1]:
                        new_record_data = {
                            'pin': temp_list[0],
                            'clock_in_time': datetime.strptime(temp_list[1], '%Y-%m-%d %H:%M:%S') - timedelta(hours=8)
                        }
                        attendance_models.sudo().create(new_record_data)

                        # 考勤记录
                        attendance_record.sudo().clock_in(temp_list)
                        return 'ok'
                except Exception as e:
                    with open('attendance_error_time.txt', 'a+') as f:
                        f.write(str(temp_list) + '\n')
                    _logger.exception("发生异常：")
        # 添加默认的响应
        return 'ok'
