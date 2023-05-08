# encoding: utf-8
"""
约苗公众号预约操作
"""
import os.path as osp
import time
from YuemiaoPublicAccount.linkman import get_linkmanId_by_name
from YuemiaoPublicAccount.util import save_excel
from YuemiaoPublicAccount.all_city_code import get_province_code
import YuemiaoPublicAccount.config as cfg
from YuemiaoPublicAccount.subscribe import subscribe_by_province, subscribe_by_region_id, subscribe
from YuemiaoPublicAccount.department_info import get_department_by_name, get_all_departments
from YuemiaoPublicAccount.order import order_immediately, check_order_number
from YuemiaoPublicAccount.is_arrive_vaccine import query_is_arrive_vaccine_by_province, query_is_arrive_vaccine_in_china
from YuemiaoPublicAccount.is_seckill import get_departments_info_by_province
from thirdparty.send_email import send_email


class YueMiao:
    def __init__(self, tk, cookie):
        cfg.REQ_HEADERS['tk'] = tk
        cfg.REQ_HEADERS['cookie'] = cookie

    def subscribe_by_province(self, province):
        """
        订阅该省的全部社区医院
        :param province:
        :return:
        """
        subscribe_by_province(province=province)

    def subscribe_by_region_id(self, region_id):
        linkmanId = get_linkmanId_by_name(cfg.username)
        subscribe_by_region_id(regionCode=region_id, linkmanId=linkmanId)

    def subscribe_by_name(self, name):
        count = 0
        linkmanId = get_linkmanId_by_name(cfg.username)
        departments = get_department_by_name(name=name)

        for department in departments:
            departmentCode = department['code']
            depaVaccId = department['depaVaccId']
            vaccineCode = department['vaccineCode']
            flag, registerDetailId = subscribe(depaCode=departmentCode, depaVaccId=depaVaccId, vaccineCode=vaccineCode,
                                               linkmanId=linkmanId)
            if flag:
                count += 1
        print(f'[info]: 一共订阅了{count}个社区医院')
        # subscribe(depaCode=departments['data']['regionCode'],
        #           depaVaccId=departments['data']['depaVaccId'], linkmanId=linkmanId)

    def order_by_name(self, departmentName):
        """
        通过社区医院名称来预约
        :param departmentName:
        :return:
        """
        if cfg.customId not in cfg.VACCINDE_INFO:
            print(f'[error]: 配置文件中疫苗的规格“customId”配置有误，需要从{cfg.VACCINDE_INFO.keys()}中选择')
            print(cfg.VACCINDE_INFO)
            exit()
        print('#' * 50)
        print('#' * 20 + ' 抢苗信息 ' + '#' * 20)
        print(f'抢苗用户：{cfg.username}')
        print(f"抢苗规格：{cfg.VACCINDE_INFO[cfg.customId]}")
        print(f"抢苗的社区医院：{departmentName}")
        print('#' * 50)
        print()

        print('开始搜索抢苗...')

        departments = get_department_by_name(name=departmentName)
        if len(departments) == 0:
            print(f'[error]: 您输入的社区名字"{departmentName}"暂时没有找到...')
            exit()

        print(f'[info]: 一共查找到{len(departments)}个与"{departmentName}"相关的社区医院')

        linkmanId = get_linkmanId_by_name(cfg.username)
        if linkmanId is None:
            print(f'[error]: 输入的用户名 {cfg.username} 没有在系统中注册')
            return 0
        while True:

            for department in departments:
                print()
                print(f"[info]: 处理{department['name']}社区医院...")
                departmentCode = department['code']
                departmentVaccineId = department['depaVaccId']

                result = order_immediately(departmentCode=departmentCode, departmentVaccineId=departmentVaccineId,
                                           linkmanId=linkmanId)
                # print('re:', result)
                if result is None:
                    print('预约失败...')
                else:
                    print('预约成功')
                    return True
                time.sleep(5)

    def find_is_order(self, province=None, regionCode=None):
        """
        通过省份来查找是否有可预约的社区信息。一直循环查找，比如：
            当该省份的所有社区医院都查询一遍之后还没有可预约的社区，则继续重复再一次查找一遍该省份的所有社区；
            这样一直循环下去，直到有一个社区可以预约为止。
        :param province: 省份名称
        :param regionCode: 查询的区域id；如果该区域id不为空，则直接使用这个区域id来查询，跳过省份信息
        :return:
        """
        if province is None and regionCode is None:
            print('请输入省份或者区域id')
            exit()
        if cfg.customId not in cfg.VACCINDE_INFO:
            print(f'[error]: 配置文件中疫苗的规格“customId”配置有误，需要从{cfg.VACCINDE_INFO.keys()}中选择')
            print(cfg.VACCINDE_INFO)
            exit()
        print('#' * 50)
        print('#' * 20 + ' 抢苗信息 ' + '#' * 20)
        print(f'抢苗用户：{cfg.username}')
        print(f"抢苗规格：{cfg.VACCINDE_INFO[cfg.customId]}")

        if regionCode is None:
            regionCode = get_province_code(province=province)
            print(f"抢苗的省份：{province}")
        else:
            print(f"抢苗的区域id为：{regionCode}")
        print('#' * 50)
        print()

        print('开始搜索抢苗...')

        linkmanId = get_linkmanId_by_name(cfg.username)
        if linkmanId is None:
            print(f'[error]: 输入的用户名 {cfg.username} 没有在系统中注册')
            return False

        success = ""
        index = 1
        while True:
            time_start = time.time()
            # 一遍又一遍的首先查找区域所有的医院，然后再遍历每一个医院开始预约
            departments = get_all_departments(regionCode=regionCode)
            if len(departments) == 0:
                print(f'[error]: 您输入的省份"{province}"暂时没有找到存在的社区医院...')
                exit()
            print(f'第{index}次轮询查找：')
            print(f'[info]: 在{province}中一共查找到{len(departments)}个社区医院')

            can_order = []

            for department in departments:

                departmentCode = department['code']
                departmentVaccineId = department['depaVaccId']
                name = department['name']
                print()
                print(f'[info]: 查询"{name}"社区信息')
                result = check_order_number(departmentCode=departmentCode, departmentVaccineId=departmentVaccineId,
                                            linkmanId=linkmanId)
                # print('re:', result)
                if result is None or result == 0:
                    print(f'"{name}"社区医院可预约人数为0...')
                else:
                    print(f'"{name}"社区医院可以预约')
                    content = str(department) + '\n' + str(result)
                    can_order.append(content)
                    send_email(content, subject="约苗疫苗可预约")
                                # return True
                time.sleep(5)
            if can_order:
                print(f'[info]: 一共有{len(can_order)}个社区医院可以预约')
                send_email(',\n'.join(can_order), subject="约苗疫苗可预约")
                return True
            time_end = time.time()
            print(f'[info]: 第{index}轮查找耗时{time_end - time_start}\n\n')
            index += 1

    def query_arrive_vaccine_by_province(self, province):
        result = query_is_arrive_vaccine_by_province(province=province)
        save_excel(
            result,
            osp.join(
                cfg.save_departments_info_root,
                cfg.VACCINDE_INFO[cfg.customId],
                f'{province}_社区疫苗已经到苗.xls',
            ),
        )

    def query_arrive_vaccine_in_china(self):
        result = query_is_arrive_vaccine_in_china()
        save_excel(result, osp.join(cfg.save_departments_info_root, cfg.VACCINDE_INFO[cfg.customId],
                                    '全国社区疫苗已经到苗.xls'))

    def get_all_departments_by_province(self, province):
        departments = get_departments_info_by_province(province=province)
        save_excel(
            departments,
            osp.join(
                cfg.save_departments_info_root,
                cfg.VACCINDE_INFO[cfg.customId],
                f'{province}_社区信息.xls',
            ),
        )

    def get_all_departments_by_name(self, name):
        departments = get_department_by_name(name=name)
        save_excel(
            departments,
            osp.join(
                cfg.save_departments_info_root,
                cfg.VACCINDE_INFO[cfg.customId],
                f'{name}_社区信息.xls',
            ),
        )
        print(departments)
        print(f'[info]: 保存关于社区"{name}"的信息成功')

    def get_all_departments_by_code(self, regionCode):
        departments = get_all_departments(regionCode=regionCode)
        save_excel(
            departments,
            osp.join(
                cfg.save_departments_info_root,
                cfg.VACCINDE_INFO[cfg.customId],
                f'{regionCode}_社区信息.xls',
            ),
        )
        print(f'[info]: 保存"{regionCode}"编码地区的信息成功')
