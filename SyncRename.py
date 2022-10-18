# encoding=utf-8
import string
import re
import collections
import sys
import urllib
from urlparse import urlparse
from com.pnfsoftware.jeb.client.api import IScript
from com.pnfsoftware.jeb.client.api import IScript, IGraphicalClientContext
from com.pnfsoftware.jeb.core import RuntimeProjectUtil
from com.pnfsoftware.jeb.core.events import JebEvent, J
from com.pnfsoftware.jeb.core.output import AbstractUnitRepresentation, UnitRepresentationAdapter
from com.pnfsoftware.jeb.core.units.code import ICodeUnit, ICodeItem, ICodePackage
from com.pnfsoftware.jeb.core.units.code.java import IJavaSourceUnit, IJavaStaticField, IJavaNewArray, IJavaConstant, IJavaCall, IJavaField, IJavaMethod, IJavaClass
from com.pnfsoftware.jeb.core.actions import ActionTypeHierarchyData
from com.pnfsoftware.jeb.core.actions import ActionRenameData
from com.pnfsoftware.jeb.core.util import DecompilerHelper
from com.pnfsoftware.jeb.core.output.text import ITextDocument
from com.pnfsoftware.jeb.core.units.code.android import IDexUnit
from com.pnfsoftware.jeb.core.actions import ActionOverridesData
from com.pnfsoftware.jeb.core.units import UnitUtil
from com.pnfsoftware.jeb.core.units import UnitAddress
from com.pnfsoftware.jeb.core.actions import Actions, ActionContext, ActionCommentData, ActionRenameData, ActionXrefsData
import time

rename_task = []

def sub_equal(str1, str2):
    if re.sub("__[a-z]*", "", str1) == re.sub("__[a-z]*", "", str2):
        return True
    else:
        return False


class SyncRename(IScript):
    def run(self, ctx):

        defaultValue = ""
        caption = "SyncRename"
        message = "input the package:"
        input = ctx.displayQuestionBox(caption, message, defaultValue)
        print(input)
        self.sync_package = "L"+str(input).strip().replace(".","/")
        # self.sync_package = "Lokhttp3"
        # print(self.sync_package)

        self.prj = ctx.getEnginesContext().getProjects()[0]
        print(self.prj, self.prj.getArtifactCount())

        self.rename_flag = True
        while self.rename_flag:
            self.rename_flag=False
            self.project_work()
            self.rename_work()
        # self.recover_name_work()
        print("----script over!!!")

    def project_work(self):
        pass
        class_list_list = []
        bytecode_unit_list = []
        for n, liveArtifact in enumerate(self.prj.getLiveArtifacts()):
            print("\n\n\n\n")
            print("---------artifact%d:%s" % (n, liveArtifact))
            class_list = []
            for unit in liveArtifact.getUnits():
                print(unit, unit.getClass())
                for bytecode_unit in UnitUtil.findChildrenByName(unit, "Bytecode"):
                    print("bytecode_unit", bytecode_unit, bytecode_unit.getClass())

                    # for pkg in bytecode_unit.getPackages():
                    #     if str(pkg.getName()) == "None": continue
                    #     if not str(pkg.getAddress()).startswith(self.sync_package): continue
                    #     if not str(pkg.getAddress()) == "Lokhttp3/internal/a/": continue
                    #     print("pkg:", pkg, pkg.getName())
                    #     print("address:", pkg.getAddress())
                    #     self.rename_unit(pkg,bytecode_unit,"hello_a")
                    # continue

                    for cla in bytecode_unit.getClasses():
                        if not str(cla.getAddress()).startswith(self.sync_package): continue
                        # if str(cla.getName()) != "Response": continue  #test
                        class_list.append(cla)
            bytecode_unit_list.append(bytecode_unit)
            class_list_list.append(class_list)

        class_list1, class_list2 = class_list_list
        # print(class_list1)
        # print(class_list2)
        for c1 in class_list1:
            # print(c1)
            # print("super1:",c1.getSupertypes()[0])
            # print("super2:",c1.getSupertypes()[0].getImplementingClass())
            # print("supers_len:",len(c1.getSupertypes()))
            # print("interfaces:", c1.getImplementedInterfaces())
            # print("interfaces_len:", len(c1.getImplementedInterfaces())
            # print("package:", c1.getPackage())
            # continue
            for c2 in class_list2:
                if sub_equal(c1.getAddress(), c2.getAddress()):
                    print("sync_class:", c1, c2)
                    self.sync_class(c1, c2, bytecode_unit_list[0], bytecode_unit_list[1])
                    break

        # self.sync_class(class_list1[0], class_list2[0], bytecode_unit_list[0], bytecode_unit_list[1])

    def rename_work(self):
        print("------rename work:")
        for x in set(rename_task):
            if sub_equal(x[0].getName(), x[1].getName()): continue
            print(x)
            self.sync_unit_name(x[0], x[1], x[2])

    def recover_name_work(self):
        for n, liveArtifact in enumerate(self.prj.getLiveArtifacts()):
            if n != 1: continue
            print("\n\n---------artifact%d:%s" % (n, liveArtifact))
            for unit in liveArtifact.getUnits():
                print(unit, unit.getClass())
                for bytecode_unit in UnitUtil.findChildrenByName(unit, "Bytecode"):
                    print("bytecode_unit", bytecode_unit, bytecode_unit.getClass())
                    for cla in bytecode_unit.getClasses():
                        self.recover_unit_name(cla, bytecode_unit)
                    for mtd in bytecode_unit.getMethods():
                        self.recover_unit_name(mtd, bytecode_unit)
                    for fi in bytecode_unit.getFields():
                        # print(fi)
                        self.recover_unit_name(fi, bytecode_unit)

    def sync_class(self, class1, class2, bytecode_unit1, bytecode_unit2):
        # sync super
        super_class1 = class1.getSupertypes()[0].getImplementingClass()
        super_class2 = class2.getSupertypes()[0].getImplementingClass()
        # print("class_&_su:",class1,super_class1)
        # print("class_&_su:",class2,super_class2)
        if super_class1 and super_class2 and super_class1.getName() != "Object" and super_class2.getName() != "Object" and super_class1.getName() != super_class2.getName():
            self.sync_class(super_class1, super_class2, bytecode_unit1, bytecode_unit2)

        # sync interface

        # sync Inner Class

        # sync fields
        fields1 = class1.getFields()
        fields2 = class2.getFields()

        idx_pops1 = []
        idx_pops2 = []
        for n1, x1 in enumerate(fields1):
            for n2, x2 in enumerate(fields2):
                if sub_equal(x1.getAddress(), x2.getAddress()):
                    idx_pops1.append(n1)
                    idx_pops2.append(n2)
                    break
        for n, x in enumerate(set(idx_pops1)):
            fields1.pop(x - n)
        for n, x in enumerate(set(idx_pops2)):
            fields2.pop(x - n)

        field1_names = []
        field1_types = []
        field2_names = []
        field2_types = []

        for x in fields1:
            name, type = str(x.getAddress()).split(":")
            field1_names.append(name)
            field1_types.append(type)
        for x in fields2:
            name, type = str(x.getAddress()).split(":")
            field2_names.append(name)
            field2_types.append(type)

        for x1 in fields1:
            field_name1, field_ret1 = str(x1.getAddress()).split(":")
            # print("field1:", field_name1, field_ret1)
            for x2 in fields2:
                field_name2, field_ret2 = str(x2.getAddress()).split(":")
                # print("field2:", field_name2, field_ret2)

                is_equal = False
                if sub_equal(field_name1, field_name2) or \
                        (sub_equal(field_ret1, field_ret2) and field1_types.count(field_ret1) == 1 and field2_types.count(field_ret2) == 1):
                    is_equal = True

                if is_equal:
                    print("sync_field:", x1.getAddress(), x2.getAddress())
                    rename_task.append((x1, x2, bytecode_unit2))
                    rename_task.append((x1.getFieldType(), x2.getFieldType(), bytecode_unit2))
                    # if not sub_equal(field_name1, field_name2):
                    #     rename_task.append((x1, x2, bytecode_unit2))
                    # if not sub_equal(field_ret1, field_ret2):
                    #     rename_task.append((x1.getFieldType(), x2.getFieldType(), bytecode_unit2))
                    break

        # sync methods
        methods1 = class1.getMethods()
        methods2 = class2.getMethods()

        # 剔除相等不需要重命名的method
        idx_pops1 = []
        idx_pops2 = []
        for n1, x1 in enumerate(methods1):
            for n2, x2 in enumerate(methods2):
                if sub_equal(x1.getAddress(), x2.getAddress()):
                    if (x1.getAddress().find("Lokhttp3/HttpUrl") != -1):
                        print("ppop:", x1.getAddress(), x2.getAddress())
                    idx_pops1.append(n1)
                    idx_pops2.append(n2)
                    break
        for n, x in enumerate(set(idx_pops1)):
            methods1.pop(x - n)
        for n, x in enumerate(set(idx_pops2)):
            methods2.pop(x - n)

        method1_names = []
        method1_argss = []
        method1_rets = []
        method1_argss_rets = []
        method1_names_rets = []
        method1_names_argss = []
        method2_names = []
        method2_argss = []
        method2_rets = []
        method2_argss_rets = []
        method2_names_rets = []
        method2_names_argss = []

        for x in methods1:
            match_obj = re.match(r'(.*)\((.*)\)(.*)', str(x.getAddress()))
            method1_names.append(match_obj.group(1))
            method1_argss.append(match_obj.group(2))
            method1_rets.append(match_obj.group(3))
            method1_argss_rets.append([match_obj.group(2), match_obj.group(3)])
            method1_names_rets.append([match_obj.group(1), match_obj.group(3)])
            method1_names_argss.append([match_obj.group(1), match_obj.group(2)])
        # print("method1_argss_rets:", method1_argss_rets)
        for x in methods2:
            match_obj = re.match(r'(.*)\((.*)\)(.*)', str(x.getAddress()))
            method2_names.append(match_obj.group(1))
            method2_argss.append(match_obj.group(2))
            method2_rets.append(match_obj.group(3))
            method2_argss_rets.append([match_obj.group(2), match_obj.group(3)])
            method2_names_rets.append([match_obj.group(1), match_obj.group(3)])
            method2_names_argss.append([match_obj.group(1), match_obj.group(2)])

        for m1 in methods1:
            # print(m1.getAddress())
            ###Lokhttp3/Response;->header(Ljava/lang/String;Ljava/lang/String;)Ljava/lang/String;
            matchobj1 = re.match(r'(.*)\((.*)\)(.*)', str(m1.getAddress()))
            m1_name = matchobj1.group(1)
            m1_args = matchobj1.group(2)
            m1_ret = matchobj1.group(3)
            # print(m1_name, m1_args, m1_ret)
            if m1_name == "Lokhttp3/HttpUrl;->encodedPathSegments":
                # print(ddict1)
                print("method1_argss_rets:", method1_argss_rets)
            ddict1 = {
                "name": [m1_name, method1_names.count(m1_name), [m1], {m1_args, m1_ret}, method1_argss_rets.count({m1_args, m1_ret})],
                "args": [m1_args, method1_argss.count(m1_args), m1.getParameterTypes(), {m1_name, m1_ret}, method1_names_rets.count({m1_name, m1_ret})],
                "ret": [m1_ret, method1_rets.count(m1_ret), [m1.getReturnType()], {m1_name, m1_args}, method1_names_argss.count({m1_name, m1_args})]
            }
            # print(ddict1)
            for m2 in methods2:
                # print(m2.getAddress())
                matchobj2 = re.match(r'(.*)\((.*)\)(.*)', str(m2.getAddress()))
                m2_name = matchobj2.group(1)
                m2_args = matchobj2.group(2)
                m2_ret = matchobj2.group(3)
                # print(m2_name, m2_args, m2_ret)
                ddict2 = {
                    "name": [m2_name, method2_names.count(m2_name), [m2], {m2_args, m2_ret}, method2_argss_rets.count({m2_args, m2_ret})],
                    "args": [m2_args, method2_argss.count(m2_args), m2.getParameterTypes(), {m2_name, m2_ret}, method2_names_rets.count({m2_name, m2_ret})],
                    "ret": [m2_ret, method2_rets.count(m2_ret), [m2.getReturnType()], {m2_name, m2_args}, method2_names_argss.count({m2_name, m2_args})]
                }

                is_equal = False
                for n, key in enumerate(ddict1.keys()):
                    # print("nnn:",n)
                    # if
                    if (ddict1.values()[n][0] == ddict2.values()[n][0] and ddict1.values()[n][1] == 1 and ddict2.values()[n][1] == 1) \
                            or (ddict1.values()[n][3] == ddict2.values()[n][3] and ddict1.values()[n][4] == 1 and ddict2.values()[n][4] == 1):
                        # print("ddict1:", ddict1)
                        # print("ddict2:", ddict2)
                        is_equal = True
                        break
                if is_equal == True:
                    for nn in range(3):  # sync [method_name],[method_args],[method_ret]
                        # print("sync_methods:", ddict1.values()[nn][2], ddict2.values()[nn][2])
                        for nnn in range(len(ddict1.values()[nn][2])):  # sync method_name,method_args,method_ret
                            rename_task.append((ddict1.values()[nn][2][nnn], ddict2.values()[nn][2][nnn], bytecode_unit2))

                            # if not sub_equal(ddict1.values()[nn][2][nnn].getName(), ddict2.values()[nn][2][nnn].getName()):
                            #     print("sync_method:", ddict1.values()[nn][2][nnn], ddict2.values()[nn][2][nnn])
                            #     rename_task.append((ddict1.values()[nn][2][nnn], ddict2.values()[nn][2][nnn], bytecode_unit2))
                    break

    def rename_unit(self, unit, bytecode_unit, new_name):
        if str(unit.getClass()) == "<type 'com.pnfsoftware.jebglobal.EF'>":
            unit = unit.getImplementingClass()
        actCntx = ActionContext(bytecode_unit, Actions.RENAME, unit.getItemId(), unit.getAddress())
        actData = ActionRenameData()
        if bytecode_unit.prepareExecution(actCntx, actData):
            try:
                actData.setNewName(new_name)
                bRlt = bytecode_unit.executeAction(actCntx, actData)
            except Exception as e:
                print(e)

    def sync_unit_name(self, unit1, unit2, bytecode_unit):
        '''
        :param unit1:
        :param unit2:
        :param bytecode_unit:
        :return:
        todo : if package different，iterate rename package
        '''
        if str(unit1.getClass()) == "<type 'com.pnfsoftware.jebglobal.EF'>":
            unit1 = unit1.getImplementingClass()
            unit2 = unit2.getImplementingClass()
        if str(unit1.getName()).find("__") != -1 or str(unit2.getName()).find("__") != -1:
            return
        newName = unit1.getName() + "__" + unit2.getName()
        self.rename_unit(unit2, bytecode_unit, newName)
        self.rename_flag=True

        # actCntx = ActionContext(bytecode_unit, Actions.RENAME, unit2.getItemId(), unit2.getAddress())
        # actData = ActionRenameData()
        # if bytecode_unit.prepareExecution(actCntx, actData):
        #     try:
        #         newName = unit1.getName() + "__" + unit2.getName()
        #         actData.setNewName(newName)
        #         bRlt = bytecode_unit.executeAction(actCntx, actData)
        #
        #     except Exception as e:
        #         print(e)

    def recover_unit_name(self, unit, bytecode_unit):
        if str(unit.getClass()) == "<type 'com.pnfsoftware.jebglobal.EF'>":
            unit = unit.getImplementingClass()
        if str(unit.getName()).find("__") == -1: return
        if not str(unit.getAddress()).startswith(self.sync_package): return
        print("recover_name_unit:", unit)
        actCntx = ActionContext(bytecode_unit, Actions.RENAME, unit.getItemId(), unit.getAddress())
        actData = ActionRenameData()
        if bytecode_unit.prepareExecution(actCntx, actData):
            try:
                newName = ""
                actData.setNewName(newName)
                bRlt = bytecode_unit.executeAction(actCntx, actData)
            except Exception as e:
                print(e)

