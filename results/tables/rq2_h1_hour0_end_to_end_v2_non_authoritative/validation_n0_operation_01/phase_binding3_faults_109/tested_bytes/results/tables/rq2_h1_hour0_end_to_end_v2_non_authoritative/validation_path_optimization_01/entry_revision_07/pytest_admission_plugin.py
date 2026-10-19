"""Check invocation boundaries while always allowing fixture teardown."""
import pytest


class AdmissionPlugin:
    def __init__(self,policy):
        self.policy=policy

    @pytest.hookimpl(tryfirst=True)
    def pytest_configure(self,config):
        self.policy.begin_pytest(config)

    @pytest.hookimpl(trylast=True)
    def pytest_collection_finish(self,session):
        self.policy.admit('after_collection_before_fixtures')

    @pytest.hookimpl(hookwrapper=True,tryfirst=True)
    def pytest_runtest_setup(self,item):
        self.policy.admit('setup_entry:'+item.nodeid)
        try:yield
        finally:self.policy.admit('setup_exit:'+item.nodeid)

    @pytest.hookimpl(hookwrapper=True,tryfirst=True)
    def pytest_runtest_call(self,item):
        self.policy.admit('call_entry:'+item.nodeid)
        try:yield
        finally:self.policy.admit('call_exit:'+item.nodeid)

    @pytest.hookimpl(hookwrapper=True,tryfirst=True)
    def pytest_runtest_teardown(self,item,nextitem):
        entry_error=None
        try:self.policy.admit('teardown_entry:'+item.nodeid)
        except BaseException as error:entry_error=error
        try:yield
        finally:
            exit_error=None
            try:self.policy.admit('teardown_exit:'+item.nodeid)
            except BaseException as error:exit_error=error
            if entry_error is not None:raise entry_error
            if exit_error is not None:raise exit_error
