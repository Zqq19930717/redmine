#!/usr/bin/env python
# -*- encoding: utf-8 -*-
'''
@Peoject :   redmine
@Author  ：  quanquanzhou    
@DateTime :  2022/7/12 17:27
@Desc :
'''

class BootstrapForm():
    bootstrap_class_exclude = []
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # 循环找到所有的字段，添加一个css样式
        for fields, fields_obj in self.fields.items():
            if fields in self.bootstrap_class_exclude:
                continue
            # print(fields, fields_obj)   # fileds和fields_obj对应username <django.forms.fields.CharField object at 0x000001837F682D60>
            # 调整优化，如果字段中有属性，保留原来的属性并增加想要的属性，没有属性，才新建一个属性字典
            if fields_obj.widget.attrs:
                # print(fields_obj.widget.attrs)  # 比如已经有了{'minlength': '8'}, {'step': '0.01'}等, 直接新建字典会覆盖掉
                # fields_obj.widget.attrs["class"] = "form-control"
                old_class = fields_obj.widget.attrs.get('class', "") # 先获取已有的class属性，有的话取到，往后面加class属性，没有取""往后面加属性
                fields_obj.widget.attrs['class'] = '{} form-control'.format(old_class)
                fields_obj.widget.attrs["placeholder"] = fields_obj.label
            else:
                fields_obj.widget.attrs= {"class": "form-control", "placeholder": fields_obj.label}