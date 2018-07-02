import time
import base_model
from .helper import Helper
from datetime import datetime
from .criteria import Criteria
from .dataType import TimeStampField
from google.cloud.spanner_v1.streamed import StreamedResultSet
from google.api_core.datetime_helpers import DatetimeWithNanoseconds


class DataParser(object):
    @classmethod
    def parse_result_set(cls, result_set, select_cols):
        """
        Parse result set

        :type result_set: StreamedResultSet
        :param result_set:

        :type select_cols: list
        :param select_cols:

        :rtype: list
        :return: parsed results
        """
        data = []
        for row in result_set:
            row_data = {}
            index = 0

            for field in select_cols:
                if isinstance(row[index], unicode):
                    value = str(row[index])
                elif isinstance(row[index], DatetimeWithNanoseconds):
                    value = time.mktime(row[index].timetuple())
                else:
                    value = row[index]

                row_data[field] = value
                index += 1
            data.append(row_data)

        return data

    @classmethod
    def map_model(cls, result_set, select_cols, model_class):
        """
        Map result set to model

        :type result_set: StreamedResultSet
        :param result_set: result set

        :type select_cols: list
        :param select_cols:

        :type model_class: base_model.BaseModel
        :param model_class:

        :rtype: list
        :return: list of result set
        """
        parse_results = cls.parse_result_set(result_set, select_cols)
        table_name = model_class._meta().db_table
        column_prop_maps = cls.model_column_attr_maps(model_class, table_name)

        data_list = []
        for result in parse_results:
            model_object = model_class()
            model_object._state().is_new = False
            for column_name in column_prop_maps:
                model_prop = getattr(model_object, column_prop_maps.get(column_name))
                model_prop.value = result.get(column_name)

            data_list.append(model_object)

        return data_list

    @classmethod
    def model_column_attr_maps(cls, model_class, alis=None):
        """
        Map model props with db columns

        :type model_class: base_model.BaseModel
        :param model_class:

        :rtype: dict
        :return: db column mapper to model attrs
        """
        attrs = Helper.get_model_attrs(model_class)
        property_column_map = {}
        for attr_name, attr in attrs.items():
            if alis is None:
                property_column_map[attr.db_column] = attr_name
            else:
                property_column_map[alis + '.' + attr.db_column] = attr_name

        return property_column_map

    @classmethod
    def parse_raw_data(cls, model_cls, raw_data_list, insert=True):
        """
        Parse raw data for insert

        :type model_cls: base_model.BaseModel
        :param model_cls: model class

        :type raw_data_list: list
        :param raw_data_list: raw data list eg. [{'name': 'sanish', 'user_name': 'mjsanish'}]

        :type insert: bool
        :param insert: insert data or not

        :rtype: dict
        :return: {'columns': list, 'data_list': list, 'model_list': list}
        """
        model_obj_list = []
        pk_list = []
        primary_key_name = model_cls._meta().primary_key

        data_sets = {}
        for data in raw_data_list:
            if insert is False and data.get(primary_key_name) is None:
                raise AttributeError('Update data should have primary key value')
            elif insert and data.get(primary_key_name) is None:
                pk = model_cls._meta().generate_pk()
            else:
                pk = data.get(primary_key_name)

            pk_list.append(pk)
            data_sets[pk] = data

        if insert is False:
            criteria = Criteria()
            criteria.add_condition((model_cls.primary_key_property(), 'IN', pk_list))
            model_obj_list = model_cls.find_all(criteria)
        else:
            for pk in pk_list:
                model_object = Helper.init_model_with_default(model_cls)
                model_object.__setattr__(primary_key_name, pk)
                model_object._state().is_new = True
                model_obj_list.append(model_object)

        for model in model_obj_list:
            pk = model.get_pk_value()
            data = data_sets.get(pk)
            for key in data:
                if model.has_property(key):
                    model.__setattr__(key, data.get(key))

        return cls.build_model_data(model_cls, model_obj_list)

    @classmethod
    def build_model_data(cls, model_cls, model_obj_list):
        """
        Build model data that can be use for save (add/update)

        :type model_cls: base_model.BaseModel
        :param model_cls:

        :type model_obj_list: list
        :param model_obj_list: list of model objects

        :rtype: dict
        :return: {'columns' : list, 'data_list' : list}
        """
        data_list = []
        columns = []

        model_attrs = Helper.get_model_attrs(model_cls)
        print(model_cls)
        for model_obj in model_obj_list:
            print(model_obj)
            if model_obj.validate():
                data_tuple = ()
                for attr_name in model_attrs:
                    model_obj_attr = model_obj.__getattribute__(attr_name)
                    if isinstance(model_obj_attr, TimeStampField) and model_obj_attr.value is not None:
                        ts = datetime.fromtimestamp(model_obj_attr.value)
                        value = ts.isoformat() + 'Z'
                        data_tuple += (value,)
                    else:
                        data_tuple += (model_obj_attr.value,)

                    if model_obj_attr.db_column not in columns:
                        columns.append(model_obj_attr.db_column)

                data_list.append(data_tuple)
            else:
                raise RuntimeError('Data validation error: {}'.format(model_obj.get_errors()))

        return {
            'columns': columns,
            'data_list': data_list,
            'model_list': model_obj_list
        }
