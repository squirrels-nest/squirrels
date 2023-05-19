from __future__ import annotations
from typing import Type, Sequence, Dict, List, Iterator, Optional, Union
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
import copy

from squirrels import parameter_options as po, _utils as u
from squirrels.data_sources import DataSource
from squirrels.parameter_set import _ParameterSetBase
from squirrels._timed_imports import pandas as pd


@dataclass
class Parameter:
    name: str
    label: str
    all_options: Sequence[po.ParameterOption]
    is_hidden: bool
    parent: Optional[_SelectionParameter]

    def WithParent(all_options: Sequence[po.ParameterOption], parent: SingleSelectParameter, new_param: Parameter):
        new_param._set_parent_and_options(parent, all_options)
        new_param.parent._add_child_mutate(new_param)
        return new_param.refresh(parent)

    def refresh(self, parent: Optional[_SelectionParameter] = None) -> Parameter:
        param_copy = copy.copy(self)
        if parent is not None:
            param_copy.parent = parent
        param_copy._refresh_mutate()
        return param_copy

    def with_selection(self, _: str) -> Parameter:
        raise u.AbstractMethodCallError(self.__class__, "with_selection")
    
    def get_all_dependent_params(self) -> _ParameterSetBase:
        dependent_params = _ParameterSetBase()
        self._accum_all_dependent_params(dependent_params)
        return dependent_params
    
    def _set_default_as_selection_mutate(self) -> None:
        raise u.AbstractMethodCallError(self.__class__, "_set_default_as_selection_mutate")
    
    def _refresh_mutate(self) -> None:
        if self.parent is not None and hasattr(self, 'curr_option'):
            self.curr_option = next(self._get_valid_options_iterator())
        self._set_default_as_selection_mutate()
    
    def _get_valid_options_iterator(self) -> Iterator[po.ParameterOption]:
        selected_parent_option_ids = self.parent._get_selected_ids_as_list()
        return (x for x in self.all_options if x.is_valid(selected_parent_option_ids))
    
    def _raise_invalid_input_error(self, selection: str, more_details: str = '', e: Exception = None) -> None:
        raise u.InvalidInputError(f'Selected value "{selection}" is not valid for parameter "{self.name}". ' + more_details) from e
    
    def _verify_parent_is_single_select(self) -> None:
        if not isinstance(self.parent, SingleSelectParameter):
            raise u.ConfigurationError(f'For "{self.name}", it''s not a selection parameter, so its parent must be a SingleSelectParameter')
        
    def _verify_parent_options_have_one_child_each(self) -> None:
        accum_set = set()
        for option in self.all_options:
            if not accum_set.isdisjoint(option.parent_option_ids):
                raise u.ConfigurationError(f'For "{self.name}", it''s not a selection parameter, so no two options can share the same parent option')
            accum_set = accum_set.union(option.parent_option_ids)
        if len(accum_set) != len(self.parent.options):
            raise u.ConfigurationError(f'For "{self.name}", all parent option ids must exist across all options')
    
    def _set_parent_and_options(self, parent: SingleSelectParameter, all_options: Sequence[po.ParameterOption]) -> None:
        self.parent = parent
        self.all_options = all_options
        self._verify_parent_is_single_select()
        self._verify_parent_options_have_one_child_each()
    
    def _accum_all_dependent_params(self, param_set: _ParameterSetBase) -> None:
        param_set.add_parameter(self)
        
    def _enquote(self, value: str) -> str:
        return "'" + value.replace("'", "''") + "'" 

    def to_dict(self) -> Dict:
        return {
            'widget_type': self.__class__.__name__,
            'name': self.name,
            'label': self.label
        }


@dataclass
class _SelectionParameter(Parameter):
    def __post_init__(self) -> None:
        self.trigger_refresh: bool = False
        self.options: Sequence[po.SelectParameterOption] = tuple(self.all_options)
        self.children: List[_SelectionParameter] = list()
        if self.parent is not None:
            self.parent._add_child_mutate(self)
        self._refresh_mutate()
    
    def _add_child_mutate(self, child: Parameter) -> None:
        self.children.append(child)
        self.trigger_refresh = True
    
    def _refresh_mutate(self) -> None:
        if self.parent is not None:
            self.options = tuple(self._get_valid_options_iterator())
        self._set_default_as_selection_mutate()
        self.children = [child.refresh(self) for child in self.children]

    def _get_selected_ids_as_list(self) -> Sequence[str]:
        raise u.AbstractMethodCallError(self.__class__, "_get_selected_ids_as_list")

    def _get_default_iterator(self) -> Iterator[po.ParameterOption]:
        return (x.identifier for x in self.options if x.is_default)
    
    def _validate_selected_id_in_options(self, selected_id: str) -> str:
        if selected_id in (x.identifier for x in self.options):
            return selected_id
        else:
            self._raise_invalid_input_error(selected_id)
    
    def _accum_all_dependent_params(self, param_set: _ParameterSetBase) -> None:
        super()._accum_all_dependent_params(param_set)
        for child in self.children:
            child._accum_all_dependent_params(param_set)

    def to_dict(self):
        output = super().to_dict()
        output['options'] = [x.to_dict() for x in self.options]
        output['trigger_refresh'] = self.trigger_refresh
        return output


@dataclass
class SingleSelectParameter(_SelectionParameter):
    selected_id: Optional[str]

    def __init__(self, name: str, label: str, all_options: Sequence[po.SelectParameterOption], *, 
                 is_hidden: bool = False, parent: Optional[_SelectionParameter] = None) -> None:
        super().__init__(name, label, all_options, is_hidden, parent)
    
    def with_selection(self, selection: str) -> SingleSelectParameter:
        param_copy = copy.copy(self)
        param_copy.selected_id = self._validate_selected_id_in_options(selection)
        param_copy.children = [child.refresh(param_copy) for child in param_copy.children]
        return param_copy

    def get_selected(self) -> po.SelectParameterOption:
        return next(x for x in self.options if x.identifier == self.selected_id)
    
    def get_selected_id(self) -> str:
        return self.get_selected().identifier
    
    def get_selected_id_quoted(self) -> str:
        return self._enquote(self.get_selected_id())
    
    def get_selected_label(self) -> str:
        return self.get_selected().label
    
    def get_selected_label_quoted(self) -> str:
        return self._enquote(self.get_selected_label())
    
    # Overriding for refresh method
    def _get_selected_ids_as_list(self) -> Sequence[str]:
        return (self.get_selected_id(),)
    
    def _get_default(self) -> str:
        default_id = next(self._get_default_iterator(), None)
        if default_id is None:
            default_id = self.options[0].identifier if len(self.options) > 0 else None
        return default_id
    
    def _set_default_as_selection_mutate(self) -> None:
        self.selected_id = self._get_default()

    def to_dict(self) -> Dict:
        output = super().to_dict()
        output['selected_id'] = self.selected_id
        return output


@dataclass
class MultiSelectParameter(_SelectionParameter):
    selected_ids: Sequence[str]
    include_all: bool
    order_matters: bool

    def __init__(self, name: str, label: str, all_options: Sequence[po.SelectParameterOption], *, is_hidden = False,
                 parent: Optional[_SelectionParameter] = None, include_all: bool = True, order_matters: bool = False) -> None:
        super().__init__(name, label, all_options, is_hidden, parent)
        self.include_all = include_all
        self.order_matters = order_matters

    def with_selection(self, selection: str) -> MultiSelectParameter:
        param_copy = copy.copy(self)
        selection_split = u.load_json_or_comma_delimited_str_as_list(selection)
        param_copy.selected_ids = tuple(self._validate_selected_id_in_options(x) for x in selection_split)
        param_copy.children = [child.refresh(param_copy) for child in self.children]
        return param_copy

    def get_selected_list(self) -> Sequence[po.SelectParameterOption]:
        if len(self.selected_ids) == 0 and self.include_all:
            result = tuple(self.options)
        else:
            result = tuple(x for x in self.options if x.identifier in self.selected_ids)
        return result
    
    def get_selected_ids_as_list(self) -> Sequence[str]:
        return tuple(x.identifier for x in self.get_selected_list())
    
    def get_selected_ids_joined(self) -> str:
        return ', '.join(self.get_selected_ids_as_list())
    
    def get_selected_ids_quoted_as_list(self) -> Sequence[str]:
        return tuple(self._enquote(x) for x in self.get_selected_ids_as_list())
    
    def get_selected_ids_quoted_joined(self) -> str:
        return ', '.join(self.get_selected_ids_quoted_as_list())
    
    def get_selected_labels_as_list(self) -> Sequence[str]:
        return tuple(x.label for x in self.get_selected_list())
    
    def get_selected_labels_joined(self) -> str:
        return ', '.join(self.get_selected_labels_as_list())
    
    def get_selected_labels_quoted_as_list(self) -> Sequence[str]:
        return tuple(self._enquote(x) for x in self.get_selected_labels_as_list())
    
    def get_selected_labels_quoted_joined(self) -> str:
        return ', '.join(self.get_selected_labels_quoted_as_list())
    
    def _get_selected_ids_as_list(self) -> Sequence[str]:
        return self.get_selected_ids_as_list()
    
    def _get_default(self) -> Sequence[str]:
        return tuple(self._get_default_iterator())
    
    def _set_default_as_selection_mutate(self):
        self.selected_ids = self._get_default()

    def to_dict(self):
        output = super().to_dict()
        output['selected_ids'] = list(self.selected_ids)
        output['include_all'] = self.include_all
        output['order_matters'] = self.order_matters
        return output


@dataclass
class DateParameter(Parameter):
    curr_option: po.DateParameterOption
    selected_date: datetime

    def __init__(self, name: str, label: str, default_date: Union[str, datetime], date_format: str = '%Y-%m-%d', 
                 *, is_hidden: bool = False) -> None:
        self.curr_option = po.DateParameterOption(default_date, date_format)
        all_options = (self.curr_option,)
        super().__init__(name, label, all_options, is_hidden, None)
        self._set_default_as_selection_mutate()
    
    @staticmethod
    def WithParent(name: str, label: str, all_options: Sequence[po.DateParameterOption], parent: SingleSelectParameter, *, 
                   is_hidden: bool = False) -> DateParameter:
        new_param = DateParameter(name, label, '2020-01-01', is_hidden=is_hidden) # dummy date
        return Parameter.WithParent(all_options, parent, new_param)
    
    def with_selection(self, selection: str):
        param_copy = copy.copy(self)
        try:
            param_copy.selected_date = param_copy.curr_option._validate_date(selection)
        except u.ConfigurationError as e:
            self._raise_invalid_input_error(selection, 'Invalid selection for date.', e)
        return param_copy

    def get_selected_date(self) -> str:
        return self.selected_date.strftime(self.curr_option.date_format)

    def get_selected_date_quoted(self) -> str:
        return self._enquote(self.get_selected_date())
    
    def _set_default_as_selection_mutate(self) -> None:
        self.selected_date = self.curr_option.default_date
    
    def to_dict(self):
        output = super().to_dict()
        output['selected_date'] = self.get_selected_date()
        return output


@dataclass
class _NumericParameter(Parameter):
    curr_option: po.NumericParameterOption
    
    def to_dict(self):
        output = super().to_dict()
        output['min_value'] = str(self.curr_option.min_value)
        output['max_value'] = str(self.curr_option.max_value)
        output['increment'] = str(self.curr_option.increment)
        return output


@dataclass
class NumberParameter(_NumericParameter):
    selected_value: Decimal

    def __init__(self, name: str, label: str, min_value: po.Number, max_value: po.Number, increment: po.Number = 1, 
                 default_value: po.Number = None, *, is_hidden: bool = False) -> None:
        default_value = default_value if default_value is not None else min_value
        curr_option = po.NumberParameterOption(min_value, max_value, increment, default_value)
        all_options = (curr_option,)
        super().__init__(name, label, all_options, is_hidden, None, curr_option)
        self._set_default_as_selection_mutate()
    
    @staticmethod
    def WithParent(name: str, label: str, all_options: Sequence[po.NumberParameterOption], parent: SingleSelectParameter, *, 
                   is_hidden: bool = False) -> DateParameter:
        new_param = NumberParameter(name, label, 0, 1, is_hidden=is_hidden) # dummy values
        return Parameter.WithParent(all_options, parent, new_param)
    
    def with_selection(self, selection: str):
        param_copy = copy.copy(self)
        try:
            param_copy.selected_value = param_copy.curr_option._validate_value(selection)
        except u.ConfigurationError as e:
            self._raise_invalid_input_error(selection, 'Invalid selection for number parameter.', e)
        return param_copy

    def get_selected_value(self) -> str:
        return str(self.selected_value)
    
    def _set_default_as_selection_mutate(self) -> None:
        self.curr_option: po.NumberParameterOption
        self.selected_value = self.curr_option.default_value
        
    def to_dict(self):
        output = super().to_dict()
        output['selected_value'] = self.get_selected_value()
        return output


@dataclass
class NumRangeParameter(_NumericParameter):
    selected_lower_value: Decimal
    selected_upper_value: Decimal

    def __init__(self, name: str, label: str, min_value: po.Number, max_value: po.Number, increment: po.Number = 1, 
                 default_lower_value: po.Number = None, default_upper_value: po.Number = None, *, is_hidden: bool = False) -> None:
        default_lower_value = default_lower_value if default_lower_value is not None else min_value
        default_upper_value = default_upper_value if default_upper_value is not None else max_value
        curr_option = po.NumRangeParameterOption(min_value, max_value, increment, default_lower_value, default_upper_value)
        all_options = (curr_option,)
        super().__init__(name, label, all_options, is_hidden, None, curr_option)
        self._set_default_as_selection_mutate()
    
    @staticmethod
    def WithParent(name: str, label: str, all_options: Sequence[po.NumRangeParameterOption], parent: SingleSelectParameter, *, 
                   is_hidden: bool = False) -> DateParameter:
        new_param = NumRangeParameter(name, label, 0, 1, is_hidden=is_hidden) # dummy values
        return Parameter.WithParent(all_options, parent, new_param)
    
    def with_selection(self, selection: str):
        try:
            lower, upper = selection.split(',')
        except ValueError as e:
            self._raise_invalid_input_error(selection, "Range parameter selection must be two numbers joined by comma.", e)

        param_copy = copy.copy(self)
        try:
            param_copy.selected_lower_value = param_copy.curr_option._validate_value(lower)
            param_copy.selected_upper_value = param_copy.curr_option._validate_value(upper, param_copy.selected_lower_value)
        except u.ConfigurationError as e:
            self._raise_invalid_input_error(selection, 'Invalid selection for range parameter.', e)
        return param_copy

    def get_selected_lower_value(self) -> str:
        return str(self.selected_lower_value)

    def get_selected_upper_value(self) -> str:
        return str(self.selected_upper_value)
    
    def _set_default_as_selection_mutate(self) -> None:
        self.curr_option: po.NumRangeParameterOption
        self.selected_lower_value = self.curr_option.default_lower_value
        self.selected_upper_value = self.curr_option.default_upper_value

    def to_dict(self):
        output = super().to_dict()
        output['selected_lower_value'] = self.get_selected_lower_value()
        output['selected_upper_value'] = self.get_selected_upper_value()
        return output


@dataclass
class DataSourceParameter(Parameter):
    parameter_class: Type[Parameter]
    data_source: DataSource
    parent: Optional[Parameter] 

    def __init__(self, parameter_class: Type[Parameter], name: str, label: str, data_source: DataSource, *, 
                 is_hidden: bool = False, parent: Optional[Parameter] = None) -> None:
        """
        Constructor for DataSourceParameter, a Parameter that uses a DataSource to convert itself to another Parameter

        Parameters:
            parameter_class: The class of widget parameter to convert to
            name: The name of the parameter
            label: The label of the parameter
            data_source: The lookup table to use for this parameter
            is_hidden: Whether or not this parameter should be hidden from parameters response
            parent: The parent parameter
        """
        super().__init__(name, label, None, is_hidden, None)
        self.parameter_class = parameter_class
        self.data_source = data_source
        self.parent = parent

    def convert(self, df: pd.DataFrame) -> Parameter:
        """
        Method to convert this DataSourceParameter into another parameter

        Parameters:
            df: The dataframe containing the parameter options data

        Returns:
            The converted parameter
        """
        return self.data_source.convert(self, df)
    
    def to_dict(self) -> Dict:
        """
        Method to convert this DataSourceParameter into a dictionary

        The field specific to this dictionary representation is "data_source".

        Returns:
            Dict: The dictionary representation of this DataSourceParameter
        """
        output = super().to_dict()
        output['widget_type'] = self.parameter_class.__name__
        output['data_source'] = self.data_source.__dict__
        return output


# Types:
SelectionParameter = Union[SingleSelectParameter, MultiSelectParameter]
NumericParameter = Union[NumberParameter, NumRangeParameter]