# @Author: South
# @Date: 2021-08-14 10:56
from pydantic import BaseSettings


class Config(BaseSettings):
    # Your Config Here

    class Config:
        extra = "ignore"
