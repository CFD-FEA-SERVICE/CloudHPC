class DataSingleton:
    _instance = None

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        if self._instance is not None:
            raise ValueError("An instantiation already exists!")
        self.all_data = {}
        self.default_data = {}
        self.multiple_struct_blueprint = {}
        self.multiple_associations = {}