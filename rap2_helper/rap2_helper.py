import json
import sys
import os
import shelve
import requests

# rap地址
rap_address = 'rap.yscredit.com'
rap_delos_address = rap_address.replace('rap', 'rap2-delos', 1)
# 临时文件
tmp_path = './rap2_helper_cache/'
tmp_file = tmp_path + 'chookie'


# 更新Rap2
def update(koa_sid, koa_sid_sig, itf, scope, params_mapping):
    # 创建header
    req_headers = {
        'Cookie': 'koa.sid=' + koa_sid + '; koa.sid.sig=' + koa_sid_sig,
        'Content-Type': 'application/json'
    }
    # 从仓库查询要处理的id
    res = requests.get('https://' + rap_delos_address + '/interface/get?id=' + itf, headers=req_headers)
    scope_str = 'response' if scope == '0' else 'request'
    properties = json.loads(res.content).get('data').get(scope_str + 'Properties')
    # 重名字段表
    name_count_map = {}
    # name -> entity
    prop_map = get_prop_map({}, name_count_map, properties, '')
    print('[INFO] 读取共[%d]个字段' % len(prop_map))
    # 创建更新属性
    upt_prop = []
    for path_name, entity in prop_map.items():
        # 取出name
        name_array = path_name.split('.')
        name = name_array[len(name_array) - 1]
        # 存在重复字段
        if name_count_map.get(name) > 1:
            print('[WARNING] 存在重名属性，请手动更新 name:{0} id:{1}'.format(path_name, entity.get('id')))
            entity['description'] = 'Check This'
        elif params_mapping.get(name):
            entity['description'] = params_mapping.get(name)
        upt_prop.append(entity)
    if len(upt_prop) == 0:
        print("[WARNING] 没有可更新的属性，更新结束")
        sys.exit()
    print('[INFO] 预计更新共[%d]个字段' % len(upt_prop))
    # 创建更新请求体
    upt_body = {
        "properties": upt_prop,
        "summary": {
            "bodyOption": "FORM_DATA",
            "requestParamsType": "QUERY_PARAMS"
        }
    }
    # 请求更新
    res = requests.post('https://' + rap_delos_address + '/properties/update?itf=' + itf, json=upt_body,
                        headers=req_headers)
    if res.status_code == 200:
        print("更新成功！")


# 获取属性映射
def get_prop_map(prop_map, name_count_map, properties, path):
    for prop in properties:
        name = prop.get('name')
        # 记录name出现次数
        if name_count_map.get(name):
            name_count_map[name] += 1
        else:
            name_count_map[name] = 1
        # 属性路径和实体的映射
        prop_map[path + name] = prop
        # 如果类型是 Array 或 Object 递归处理
        if prop.get('children'):
            get_prop_map(prop_map, name_count_map, prop.get('children'), path + name + '.')
    return prop_map


# 读取已经设置的Cookie
def read_cookie():
    if not os.path.exists(tmp_path):
        os.makedirs(tmp_file)
    with shelve.open(tmp_file) as read:  # 打开
        koa_sid = read.get("koa_sid")  # 读取 koa_sid
        koa_sid_sig = read.get("koa_sid_sig")  # 读取 koa_sid_sig
    read.close()
    return koa_sid, koa_sid_sig


# 读取已经设置的Cookie
def write_cookie(koa_sid, koa_sid_sig):
    with shelve.open(tmp_file) as write:  # 打开
        write["koa_sid"] = koa_sid  # 写
        write["koa_sid_sig"] = koa_sid_sig  # 写
    write.close()


if __name__ == '__main__':
    # 尝试读取本地缓存Cookie
    koa_sid, koa_sid_sig = read_cookie()
    if not (koa_sid or koa_sid_sig):
        print("请先登录Rap2获取Cookie")
        # Cookie
        koa_sid = input("请输入koa.sid:")
        koa_sid_sig = input("请输入koa.sid.sig:")
        # 写入缓存
        write_cookie(koa_sid, koa_sid_sig)
    else:
        print("当前缓存Cookie：")
        print("koa_sid=%s" % koa_sid)
        print("koa_sid_sig=%s" % koa_sid_sig)
        koa_sid_tmp = input("如果需要修改，请输入koa.sid （回车跳过）:")
        if koa_sid_tmp:
            koa_sid = koa_sid_tmp
            koa_sid_sig = input("请输入koa.sid.sig:")
            # 写入缓存
            write_cookie(koa_sid, koa_sid_sig)
    # 接口ID
    itf = input("请输入接口ID(点进接口，url中的itf):")
    if not itf or itf < '1':
        print('[ERROR] 接口ID不能为空或小于1')
        sys.exit()
    # 处理范围 [response = 0 | request = 1]
    scope = input("请输入处理范围[response = 0 | request = 1]默认0:")
    if not scope:
        scope = '0'
    elif scope != '0' and scope != '1':
        print('[ERROR] 处理范围只能输入[ 0 | 1 | \'\']')
        sys.exit()
    # 读取出参与描述的映射
    print("请输入出参与描述的映射（\\t分隔），输入 # 结束：")
    params_mapping = {}
    while True:
        ipt = input()
        if ipt == '#':
            break
        else:
            ipt_map = ipt.split('\t')
            if len(ipt_map) != 2:
                print("[ERROR] 出参与描述的映射输入不合法")
                sys.exit()
            params_mapping[ipt_map[0]] = ipt_map[1]
    update(koa_sid, koa_sid_sig, itf, scope, params_mapping)
