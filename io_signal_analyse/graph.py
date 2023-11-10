import matplotlib.pyplot as plt
import random
import pandas as pd


# 绘制过滤前后的输入事件数量对比图
# input_event: 输入事件
# before: 过滤前的数据
# after: 过滤后的数据
def draw_plot(input_event,before,after):
    # 解决中文显示乱码的问题
    plt.rcParams['font.sans-serif'] = ['SimHei']  # 黑体
    plt.rcParams['axes.unicode_minus'] = False  # 用来正常显示负号

    # 1、准备数据
    # 过滤前的数据
    y_before = before
    # 过滤后的数据
    y_after = after

    # 2、创建画布
    plt.figure(figsize=(13, 5))

    # 3、绘制图像
    plt.plot(input_event, y_before, color='r')
    plt.plot(input_event, y_after, color='y')
    plt.scatter(input_event, y_before, color='r')
    plt.scatter(input_event, y_after, color='y')

    # 给每个点添加其数据标签
    for i, label in enumerate(y_after):
        plt.text(input_event[i], y_after[i], label, ha='right', va='bottom')

    for i, label in enumerate(y_before):
        plt.text(input_event[i], y_before[i], label, ha='right', va='bottom')

    # 添加网格显示
    plt.grid(linestyle='--')
    # 显示图例
    plt.legend(["过滤前", "过滤后"])
    plt.xlabel("输出事件")
    plt.ylabel("输入事件数量")
    plt.title("过滤前后输入事件数量对比")

    # 4、显示图像
    plt.show()




if __name__ == "__main__":
    print("test")
