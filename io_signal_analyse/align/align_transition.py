import pm4py
import pandas
import csv
import time
from pm4py.algo.conformance.alignments.edit_distance import algorithm as logs_alignments


# 把发射序列拆解为"t+数字"构成的组合
def parse_sequence(sequence):
    transitions = []
    current_transition = ""
    # 遍历序列，先找到字母t，如果后面是数字，则进行拼接，直到下一个t
    for char in sequence:
        if char == 't':
            if current_transition:
                transitions.append(current_transition)
                current_transition = ""
            current_transition += char
        elif char.isdigit():
            current_transition += char

    # 添加最后一个变迁
    if current_transition:
        transitions.append(current_transition)

    return transitions


# "t+数字"构成的组合用单个英文字母替代
def replace_with_letters(string_list):
    if not string_list:
        return ""

    # 去重，然后进行排序
    unique_strings =  sorted(list(dict.fromkeys(string_list)), key=lambda x: int(x[1:]))

    letter_mapping = {}
    merged_string = ""

    # 构建映射表，将唯一的字符串与字母对应
    for i, string in enumerate(unique_strings):
        letter_mapping[string] = chr(97 + i)

    print(letter_mapping)

    # 遍历原始序列，依次转换为字母
    for string in string_list:
        merged_string += letter_mapping[string]

    return merged_string



# 把变迁按照开始变迁进行划分
def partition_transitions(sequence, start_transitions):
    partitions = []
    current_partition = []

    for transition in sequence:
        if transition in start_transitions and current_partition:
            partitions.append(current_partition)
            current_partition = []

        current_partition.append(transition)

    # 添加最后一个划分
    if current_partition:
        partitions.append(current_partition)

    return partitions



# 把划分好的变迁序列写入到csv文件中去
def generate_csv(partitions, filename):
    with open(filename, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['case_id', 'activity','timestamp'])

        case_id = 1
        for partition in partitions:
            for transition in partition:
                # 获取当前时间戳
                timestamp = time.time()
                # 格式化时间
                time_str = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(timestamp))
                writer.writerow([case_id, transition,time_str])
            case_id += 1



# 导入csv格式的事件日志
def import_csv(file_path):
    event_log = pandas.read_csv(file_path, sep=',')
    # 输出一个日志的基本信息
    num_events = len(event_log)
    num_cases = len(event_log.case_id.unique())
    print("Number of events: {}\nNumber of cases: {}".format(num_events, num_cases))

    # 把日志信息按照事件日志的形式进行读取解析
    event_log = pm4py.format_dataframe(event_log, case_id='case_id', activity_key='activity', timestamp_key='timestamp')

    return event_log



if __name__ == '__main__':
    # 安娜的构造的变迁序列
    ana = "t1 t2 t3 t4 t1 t2 t4 t3 t5 t6 t7 t4 t1 t2 t3 t4 t5 t6 t7 t4 t1 t2 t3 t4 t1 t2 t3 t4 t5 t6 t7 t4 t5 t6 t7 " \
          "t4 t1 t2 t3 t4 t5 t6 t7 t4 t5 t6 t7 t4 t5 t6 t7 t4 t5 t6 t7 t4 t5 t6 t7 t4 t1 t2 t4 t3 t1 t2 t3 t4 t1 t2 " \
          "t3 t4 t1 t2 t4 t3 t1 t2 t3 t4 t1"

    my = "t1 t2 t3 t1 t2 t3 t1 t2 t3 t4 t5 t6 t7 t1 t2 t3 t4 t5 t6 t7 t1 t2 t3 t1 t2 t3 t4 t5 t6 t7 " \
         "t4 t5 t6 t7 t1 t2 t3 t4 t5 t6 t8 t4 t5 t6 t8 t4 t5 t6 t3 t4 t5 t6 t7 t4 t5 t6 t7 t1 t2 t3 " \
         "t1 t2 t3 t1 t2 t3 t1 t2 t3 t1 t2 t3"


    # 将序列拆解为"t+数字"构成的组合
    ana_transitions = parse_sequence(ana)
    my_transitions = parse_sequence(my)

    # 将"t+数字"构成的组合用单个英文字母替代
    ana_merged = replace_with_letters(ana_transitions)
    print(ana_merged)
    my_merged = replace_with_letters(my_transitions)
    print(my_merged)

    # 对变迁进行划分
    # ana_partitions = partition_transitions(list(ana_merged), ['a', 'e'])
    # my_partitions = partition_transitions(list(my_merged), ['a', 'e'])
    # print(ana_partitions)
    # print(my_partitions)

    # 转化为csv文件
    generate_csv([list(ana_merged)], 'ana.csv')
    generate_csv([list(my_merged)], 'my.csv')
    # generate_csv(ana_partitions, 'ana.csv')
    # generate_csv(my_partitions, 'my.csv')


    # 读取csv文件
    ana_event_log = import_csv("ana.csv")
    my_event_log = import_csv("my.csv")


    alignments = logs_alignments.apply(my_event_log,ana_event_log)
    print(alignments)
    print(f"平均拟合度：{alignments[0].get('fitness')}")



    # 模型和日志的对齐
    # net, initial_marking, final_marking = pm4py.discover_petri_net_alpha(ana_event_log)
    # alignments_diagnostics  = pm4py.conformance_diagnostics_alignments(my_event_log,net,initial_marking,final_marking)
    # print(alignments_diagnostics)



