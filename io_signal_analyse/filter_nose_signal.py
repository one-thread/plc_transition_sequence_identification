# 过滤掉噪声信号

import find_model as fm

import pandas as pd

'''
步骤
1、计算信号的变化量
2、从变化量中切分出输入信号的变化和输出信号的变化
3、找到不同的输出信号变化量对应的输入信号变化量，转化为字典结构，key是唯一的输出信号变化量，value是对应的输入信号变化量列表
4、筛选出输出变化量中只包含单个1或者单个-1的部分，这部分代表了单个输出事件的发生
5、遍历筛选出的每一个输出信号变化量对应的输入信号变化量列表，找到包含最多0（最少1或-1）的列表，找到其他列表中和这些列表存在相同的非0元素的位置，
然后从其他列表中把这些位置上的元素修正为0，这些元素就是噪声信号。（替换为0的前提是存在一致的1或者-1，如果不一致，则保留）

问题：1、包含最多0的输入信号列表可能不止一个，这时候应该怎么处理？
         解决：把所有的包含最多0的输入信号列表都添加到max_list中，遍历所有的输入信号列表，找出匹配该信号的其他信号list，把其中噪声信号所在list中
         的下标位置，保存到dict中。
         然后再次遍历所有的输入信号其他包含噪声的输入信号列表中删除多余的元素
     2、可能存在不是包含最多0的输入列表，这个输入列表也是一个无噪声的列表，这时候应该怎么处理？
         解决：在匹配max_list的过程中，如果发现某个输入信号和任何一个都不匹配，则添加这个list到max_list中
     3、过滤完一轮噪声信号后，可能出现新的包含最多0的输入信号列表，然后需要再次过滤噪声信号，这时候应该怎么处理？
         解决：使用flag标志控制外层循环
     4、有这样的情况，即包含最多0的输入信号列表，和其他输入信号列表都不匹配，导致每一轮中都无法过滤噪声信号，这时候应该怎么处理？
        解决：把之前计算过的排除掉，重新计算参考输入列表时，即包含最多0的输入信号列表（但是0的数量比之前计算的少一个）
     5、问题4解决后产生的新问题：在排除掉都不匹配的参考输入信号列表后，新计算的参考输入信号列表，可能会计算的噪声位置和是之前排除的参考列表中
     非0项所在的位置，这时候应该怎么处理？
        解决：计算新的参考输入信号列表时，把排除列表携带过去，当遇到是排除列表中的元素时，就跳过，不参与计算
     6、当计算包含最多的输入信号列表时，找到了多个，遍历包含噪声的输入信号列表用于去除噪声时，参照列表的不同遍历顺序会导致不同的噪声信息被删除，这时候应该怎么处理？
          解决：比如情况：k1 + k1*a2 + a2 + a0*a2 + a0 + k1*a0*a2，则把包含多个的删除，保留单个的输入信号
     7、某条输入信号列表中，被其他较短的输入信号过滤后，认为该条输入信号列表中的元素都是噪声，但是全是噪声的输入信号为什么会造成输出信号的变化，这时候应该怎么处理？
'''



# 从变化量信号值中，找到输出中每个非零元素位置对应的所有输入信号列表（即每一个输出信号对应的所有输入信号）
# 参数一：变化量信号值的dataframe数据
# 参数二：输入信号的长度
# 参数三：输出信号的长度
def find_input_of_output(df,input_nums=9,output_nums=4):
    # 用字典存储不同的输出信号对应的输入信号列表
    result_dict = {}

    # 遍历每个输出位置
    for i in range(output_nums):
        position = df.columns[input_nums + i]  # 获取输出位置的列名，从例如 'A+', 'A-', 'B', 'C'
        # 获取输入信号的列
        input_columns = df.columns[:input_nums]
        # 过滤非零输出对应的输入信号，需要分开到底是1还是-1
        output_realm = [1,-1]
        for realm in output_realm:
            filtered_data = df[df[position] == realm][input_columns]
            # 将输入信号行元素转换为字符类型的数组元素
            input_array = filtered_data.apply(lambda row: row.astype(str).tolist(), axis=1).tolist()
            # 去除重复的输入信号列表
            input_array = unique_list(input_array)
            # 生成输出信号的字符串
            output_string = generate_output_string(realm, index=i,total_output_nums=output_nums)
            # 将结果存储在字典中
            if len(input_array) != 0:
                result_dict[output_string] = input_array

    return result_dict

# 生成输出信号的字符串
# 参数一：该输出信号的值
# 参数二：该输出信号的输出值（非0元素）的位置
# 参数三：输出信号的总个数
def generate_output_string(output_value, index, total_output_nums=4):
    output_list = [0] * total_output_nums
    output_list[index] = output_value
    output_string = ' '.join(map(str, output_list))
    return output_string



# 找到输出事件的真实输入事件
# 参数：一个字典，key是输出信号，value是对应的输入信号列表
def find_read_input_of_output(data_dict):
    # 创建一个新的字典，用于存储去除噪声后的结果
    result_dict = {}

    # 处理每个输出值
    for output, value_list in data_dict.items():
        # 用于控制循环是否结束
        flag =  True
        rem = []
        # 用于记录需要排除的输入信号列表，这里存放着和原始输入信号列表中任意一个都不匹配的输入信号列表，因为后续需要重新计算参考输入列表和去除噪声，需要排除这些列表
        exclude_list = []
        while flag:
            # 找到同一输出值下包含最多0的列表
            # if len(value_list) != 0:
            max_list = find_max_zero_list(value_list,exclude_list=exclude_list)

            # 去除max_list中重复的列表元素
            unique_max = unique_list(max_list)

            rem,founds = remove_noise(unique_max, value_list,exclude_list=exclude_list)

            # 如果发现一个也没有匹配，则需要重新计算参考输入列表，然后再次去除噪声
            if True not in founds:
                # 重新计算参考输入列表时，需要把之前计算过的排除掉
                exclude_list.extend(unique_max)
            else:
                # 修正data_dict对应output的value_list原始输入信号列表为删除当前噪声后的结果
                value_list = unique_list(rem)
                data_dict[output] = value_list

            # 如果发现排除的输入信号列表和所有的输入信号列表一样多，则说明已经没有噪声了，可以结束循环
            if len(exclude_list) == len(value_list):
                flag = False

        # 去除最终的rem中重复的列表元素
        unique_rem = unique_list(rem)
        # 将最终删除噪声后的去重结果添加到字典中
        result_dict[output] = unique_rem

    return result_dict

# 去除噪声信号
# 参数一：可能是实际输入信号的二维列表（参考列表，假定不存在噪声），
# 参数二：包含噪声的输入信号的二维列表
# 参数三：排除列表，这个列表中的元素不参与噪声信号的处理（这里存放着和原始输入信号列表中任意一个都不匹配的输入信号列表）
# 参数四：需要删除的排除列表，这个列表中的元素不参与噪声信号的处理（这里放着和参照数组一致的内容）
def remove_noise(reference_matrices, noisy_matrix,exclude_list=None):
    # 创建一个新的矩阵，用于存储去除噪声后的结果
    result_matrix = []

    # 创建一个字典结构，用于存储噪声所在的位置，key是输入信号的在整个输入信号集合的位置下标，value是噪声在某个输入信号中的下标位置
    noise_indexs = dict()
    # 用于记录每次匹配时是否找到了某个匹配，如果发现一个也不匹配，则需要重新计算参考输入列表
    noise_founds =set()
    # 遍历包含噪声的数组，找出噪声所在的位置
    for i in range(len(noisy_matrix)):
        noise_row = noisy_matrix[i]
        noise_found = False  # 初始化噪声标志为False

        # 初始化匹配列表为空
        match_list = []
        # 遍历每个参照数组，检查是否存在匹配
        for reference_matrix in reference_matrices:
            # 将噪声数组中的元素转换为字符串，和参照数组中的元素进行比较，如果相等，则跳过，继续比较下一个元素
            noise_str = ''.join(noise_row)
            if noise_str == ''.join(reference_matrix):
                break

            match = True
            # 检查是否在相同位置上存在非0的元素
            for j in range(len(reference_matrix)):
                # 只要发现参照数组上某个元素是非0元素，而噪声数组中对应位置的元素是0，就说明不匹配
                if reference_matrix[j] != '0' and noise_row[j] == '0':
                    match = False
                    break
                # 如果发现参照数组上某个元素是非0元素，而噪声数组中对应位置的元素也是非0元素，但是两者不相等，也说明不匹配
                if reference_matrix[j] != '0' and noise_row[j] != '0' and reference_matrix[j] != noise_row[j]:
                    match = False
                    break

            if match:
                noise_found = True
                match_list = reference_matrix
                break  # 找到匹配，不再继续搜索

        # 如果找到匹配，则去除噪声，也就是变成和参照数组一样的元素，同时记录噪声所在的位置
        if noise_found:
            result_matrix.append(match_list)
            # 找到噪声数组中噪声所处的位置，把其下标（从0开始）添加到字典中，key是输入信号的所在的下标，value是噪声所在输入信号中的下标位置
            for j in range(len(noise_row)):
                # 如果参照数组中的元素是0，而噪声数组中对应位置的元素是非0，就说明这个位置是噪声
                if match_list[j] == '0' and noise_row[j] != '0':
                    index_str = "".join(noise_row)
                    if noise_indexs.get(index_str) is None:
                        noise_indexs[index_str] = [(j,noise_row[j])]
                    else:
                        noise_indexs[index_str].append((j,noise_row[j]))

            noise_founds.add(True)
        else:
            # 如果没有找到一个匹配，就把噪声数组中的原本的输入信号元素添加到结果数组中
            result_matrix.append(noise_row)
            noise_founds.add(False)

    # print("噪声所在的位置：")
    # print(noise_indexs)

    # 遍历所有的包含噪声信号的列表，将记录为噪声所在的位置的元素都改为0
    for res_row in result_matrix:
        # 如果存在排除列表，并且当前列表在排除列表中，就跳过，不进行噪声信号的处理
        if exclude_list is not None and res_row in exclude_list:
            continue

        # 如果当前列表是包含在max_list中，就跳过，不进行噪声信号的处理，因为这个列表的输入信号是用于参照的唯一的，不需要去除噪声
        if res_row in reference_matrices:
            continue

        #记录当前遍历的输入信号列表
        # 遍历记录的噪声所在位置的字典，其index是一个数组，包含了所有的噪声位置
        for key, index in noise_indexs.items():
            # 遍历所有的噪声位置，删除噪声
            for item in index:
                # 如果发现在该位置上的元素是非0元素，且值和噪声位置处的值相同，则把该位置的元素改为0
                # if res_row[item[0]] != '0' and res_row[item[0]] == item[1]
                if res_row[item[0]] != '0':
                    res_row[item[0]] = '0'
        # 如果发现修正后全是0，则删除这个输入信号列表
        if res_row.count('0') == len(res_row):
            result_matrix.remove(res_row)

    return result_matrix,noise_founds



# 找到同一输出值下包含最多0的输入信号列表
# 参数一：包含噪声的输入信号的二维列表
# 参数二：排除列表，这个列表中的元素不参与噪声信号的处理（这里存放着和原始输入信号列表中任意一个都不匹配的输入信号列表）
def find_max_zero_list(value_list,exclude_list=None):
    max_count = 0
    max_list = []
    # 找到同一输出值下包含最多0的列表
    for value in value_list:
        # 如果存在排除列表，并且当前列表在排除列表中，就跳过
        if exclude_list is not None and value in exclude_list:
            continue

        # 计算列表中绝对值的和
        sum_value = sum([abs(int(x)) for x in value])
        # 如果全是0，就不考虑
        if sum_value == 0:
            continue
        count = value.count('0')
        if count > max_count:
            max_count = count

    # 把所有包含最多0的列表都添加到max_list中
    for value in value_list:
        if value.count('0') == max_count:
            max_list.append(value)

    # 如果排除列表中的元素和新找到的最大列表中的元素有相同的最多的0元素，则会把这个之前已经处理过元素也添加到max_list中，所以这里需要排除
    max_list = [x for x in max_list if x not in exclude_list]

    # 如果最终发现某个输出的输入信号只有全0的情况，就设置为全0
    if len(max_list) == 0:
        max_list = ['0'] * len(value_list[0])

    return max_list



# 从字符串形式的序列[['1','0','1'],['0','1','1']]的二维列表中去除重复的列表元素
def unique_list(list):
    unique = set()
    unique_list = []
    for sublist in list:
        # 将子列表转换为字符串，以便在集合中进行比较
        sublist_str = ''.join(sublist)
        # 计算子列表中绝对值的和，如果全是0，就不考虑
        sum_input = sum(abs(int(x)) for x in sublist)
        if sum_input == 0:
            continue
        if sublist_str not in unique:
            unique_list.append(sublist)
            unique.add(sublist_str)
    return unique_list



# 过滤出指包含单个1或者单个-1的输出信号
def filter_single_num_output(original_dict):
    # 创建一个新的空字典，用于存储筛选后的键值对
    filtered_dict = {}

    # 遍历原始字典的键值对
    for signal, inputs in original_dict.items():
        # 将信号字符串拆分为整数列表
        signal_values = list(map(int, signal.split()))
        # 统计非0项的个数
        non_zero_count = sum(1 for value in signal_values if value != 0)
        # 如果非0项的个数等于1，就将这个键值对添加到新字典中
        if non_zero_count == 1:
            filtered_dict[signal] = inputs

    return filtered_dict




if __name__ == "__main__":
    # 计算变化量
    change_dict = fm.compute_change_signal("plc_data.xlsx")
    # 从信号中切分输入和输出，找到不同的输出对应的输入列表（已经去除了重复）
    df = pd.DataFrame(change_dict,columns=['k1', 'k2', 'a0', 'a1', 'a2', 'b0', 'b1', 'c0', 'c1', 'A+', 'A-', 'B','C'])
    print(df.head(5))

    # output_dict = fm.output_signal_with_input(df)
    # print("输出信号对应的输入信号列表：")
    # print(output_dict)
    # # 筛选出只包含单个1或者单个-1的输出信号
    # filter = filter_single_num_output(output_dict)
    # print("筛选出只包含单个1或者单个-1的输出信号：")
    # print(filter)
    #
    # # 遍历筛选出的每一个输出信号变化量对应的输入信号变化量列表，找到包含最多0（最少1或-1）的列表，然后从其他列表中删除多余的元素（1或-1）
    # result_dict = find_read_input_of_output(output_dict)
    # print("过滤噪声后的结果：")
    # print(result_dict)


    res = find_input_of_output(df)
    print(res)




