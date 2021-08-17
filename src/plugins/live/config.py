# @Author: South
# @Date: 2021-08-17 15:51
from pydantic import BaseSettings


class Config(BaseSettings):
    # Your Config Here

    class Config:
        extra = "ignore"