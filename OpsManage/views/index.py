#!/usr/bin/env python  
# _#_ coding:utf-8 _*_  
import random
from OpsManage.utils import base
from django.http import HttpResponseRedirect,JsonResponse
from django.shortcuts import render
from django.contrib import auth
from django.contrib.auth.decorators import login_required
from OpsManage.models import (Global_Config,Email_Config,Assets,
                              Cron_Config,Project_Order,Log_Assets,
                              Project_Config,Ansible_Playbook)
from django.contrib.auth.decorators import permission_required

@login_required(login_url='/login')
def index(request):
    #7天更新频率统计
    userList = Project_Order.objects.raw('''SELECT id,order_user FROM opsmanage_project_order GROUP BY order_user;''')
    userList = [ u.order_user for u in userList ]
    dateList = [ base.getDaysAgo(num) for num in xrange(0,7) ][::-1]#将日期反序
    dataList = []
    for user in userList:
        valueList = []
        data = dict()
        for startTime in dateList:
            sql = """SELECT id,IFNULL(count(0),0) as count from opsmanage_project_order WHERE 
                    date_format(create_time,"%%Y%%m%%d") = {startTime} and order_user='{user}'""".format(startTime=startTime,user=user)
            userData = Project_Order.objects.raw(sql) 
            if  userData[0].count == 0 :valueList.append(random.randint(1, 10)) 
            else:valueList.append(userData[0].count) 
        data[user] = valueList
        dataList.append(data) 
    #获取所有指派给自己需要审核的工单
    orderNotice = Project_Order.objects.all().order_by('-id')[0:10]
    #月度更新频率统计
    monthList = [ base.getDaysAgo(num)[0:6] for num in (0,30,60,90,120,150,180) ][::-1]
    monthDataList = []
    for ms in monthList:
        startTime = int(ms+'01')
        endTime = int(ms+'31')
        data = dict()
        data['date'] = ms
        for user in userList:
            sql = """SELECT id,IFNULL(count(0),0) as count from opsmanage_project_order WHERE date_format(create_time,"%%Y%%m%%d") >= {startTime} and 
                    date_format(create_time,"%%Y%%m%%d") <= {endTime} and order_user='{user}'""".format(startTime=startTime,endTime=endTime,user=user)
            userData = Project_Order.objects.raw(sql) 
            if  userData[0].count == 0:data[user] = random.randint(1, 100)
            else:data[user] = userData[0].count
        monthDataList.append(data)
    #用户部署总计
    allDeployList = []
    for user in userList:
        data = dict()
        count = Project_Order.objects.filter(order_user=user).count()
        data['user'] = user
        data['count'] = count 
        allDeployList.append(data)
    #获取资产更新日志
    assetsLog = Log_Assets.objects.all().order_by('-id')[0:10]
    #获取所有项目数据
    assets = Assets.objects.all().count()
    project = Project_Config.objects.all().count()
    cron = Cron_Config.objects.all().count()
    playbook = Ansible_Playbook.objects.all().count()
    projectTotal = {
                    'assets':assets,
                    'project':project,
                    'playbook':playbook,
                    'cron':cron
                    }
    return render(request,'index.html',{"user":request.user,"orderList":dataList,
                                            "userList":userList,"dateList":dateList,
                                            "monthDataList":monthDataList,"monthList":monthList,
                                            "allDeployList":allDeployList,"assetsLog":assetsLog,
                                            "orderNotice":orderNotice,"projectTotal":projectTotal})


"""
@login_required默认请求url：/login
urls.py /login --> view.index.py.login()

1.通过request获取request.session

2.django.contrib.auth
认证给出的用户名和密码，使用 authenticate() 函数。它接受两个参数，用户名 username 和 密码 password ，并在密码对给出的用户名合法的情况下返回一个 User 对象。
如果密码不合法，authenticate()返回None。
"""

def login(request):
    # 验证request.session中知否已经保存了username变量值；
    # 验证登陆后保存了会跳转到/ 根路径
    if request.session.get('username') is not None:
        return HttpResponseRedirect('/',{"user":request.user})
    else:
        username = request.POST.get('username')
        password = request.POST.get('password') 
        user = auth.authenticate(username=username,password=password)
        if user and user.is_active:
            auth.login(request,user)
            # request.session保存username变量值
            request.session['username'] = username
            # 验证成功后跳转的url
            return HttpResponseRedirect('/user/center/',{"user":request.user})
        else:
            if request.method == "POST":
                return render(request,'login.html',{"login_error_info":"用户名不错存在，或者密码错误！"},)
            # 进入登陆页面
            else:
                return render(request,'login.html') 
            
            
def logout(request):
    auth.logout(request)
    return HttpResponseRedirect('/login')

def noperm(request):
    return render(request,'noperm.html',{"user":request.user}) 

@login_required(login_url='/login')
@permission_required('OpsManage.can_change_global_config',login_url='/noperm/')
def config(request):
    if request.method == "GET":
        try: 
            config = Global_Config.objects.get(id=1)
        except:
            config = None
        try:
            email = Email_Config.objects.get(id=1)
        except:
            email =None
        return render(request,'config.html',{"user":request.user,"config":config,
                                                 "email":email})
    elif request.method == "POST":
        if request.POST.get('op') == "log":
            try:
                count = Global_Config.objects.filter(id=1).count()
            except:
                count = 0
            if count > 0:
                Global_Config.objects.filter(id=1).update(
                                                      ansible_model =  request.POST.get('ansible_model'),
                                                      ansible_playbook =  request.POST.get('ansible_playbook'),
                                                      cron =  request.POST.get('cron'),
                                                      project =  request.POST.get('project'),
                                                      assets =  request.POST.get('assets',0),
                                                      server =  request.POST.get('server',0),
                                                      email =  request.POST.get('email',0),   
                                                      webssh =  request.POST.get('webssh',0),                                                   
                                                    )
            else:
                config = Global_Config.objects.create(
                                                      ansible_model =  request.POST.get('ansible_model'),
                                                      ansible_playbook =  request.POST.get('ansible_playbook'),
                                                      cron =  request.POST.get('cron'),
                                                      project =  request.POST.get('project'),
                                                      assets =  request.POST.get('assets'),
                                                      server =  request.POST.get('server'),
                                                      email =  request.POST.get('email'),
                                                      webssh =  request.POST.get('webssh',0)
                                                    )    
            return JsonResponse({'msg':'配置修改成功',"code":200,'data':[]})   
        elif request.POST.get('op') == "email":
            try:
                count = Email_Config.objects.filter(id=1).count()
            except:
                count = 0
            if count > 0:
                Email_Config.objects.filter(id=1).update(
                                                      site =  request.POST.get('site'),
                                                      host =  request.POST.get('host',None),
                                                      port =  request.POST.get('port',None),
                                                      user =  request.POST.get('user',None),
                                                      passwd =  request.POST.get('passwd',None),
                                                      subject =  request.POST.get('subject',None),
                                                      cc_user =  request.POST.get('cc_user',None),                                                  
                                                    )
            else:
                Email_Config.objects.create(
                                            site =  request.POST.get('site'),
                                            host =  request.POST.get('host',None),
                                            port =  request.POST.get('port',None),
                                            user =  request.POST.get('user',None),
                                            passwd =  request.POST.get('passwd',None),
                                            subject =  request.POST.get('subject',None),
                                            cc_user =  request.POST.get('cc_user',None), 
                                            )    
            return JsonResponse({'msg':'配置修改成功',"code":200,'data':[]}) 
        
