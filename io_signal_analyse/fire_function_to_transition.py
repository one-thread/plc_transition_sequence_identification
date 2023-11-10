# 通过找到的触发函数，遍历原始信号变化向量，转化为变迁

import filter_nose_signal as fns

import  pandas as pd

from process_mining import build_petrinet as bp

from collections import OrderedDict

import graph as gp


"""
输入参数：1、信号变化量列表；2、触发函数（key-value，其中key是输出，value是其对应的输入）
步骤：
1、遍历信号变化量列表，对于每一个信号变化量，查找触发函数dict中是否有相同的输出，
如果有，就在该输出中查找对应的输入列表，如果当前信号变化量的输入在输入列表中，就将其标记为一个字母，然后将字母添加到变迁中
2、如果没有找到匹配的输出，可以进行相应的处理

3、修正：
    （1）输入信号的对比中，需要分为两种情况，一种是当前信号的输入部分在触发函数的输入列表中，表示该信号是不带有噪声的一个信号，
    另一种是当前信号的输入部分不在触发函数的输入列表中，表示该信号是带有噪声的一个信号，需要逐个比较对应的非0项所在的位置，检查
    是否在相同的索引位置存在相同的非零元素，其余位置视为噪声，可以忽略不计。
    （2）如果当前输出信号中非零元素存在多个，即同一信号序列中检测到了多个的输出值，则分别找到对应的位置的单一输出信号，匹配其对应的输入信号
    （3）在多个输出值处于同一信号序列中的情况下，需要考虑是否是相同的输入导致的，从而用一个变迁表示这个行为（这认为是一种并发的关系），而不应该
    分别构造不同的变迁，因为这种拆分顺序是不确定的，可能出现异常情况。
    （4）多个输入值也需要进行分析，如果是相同的输入导致了不同的输出，则构造一个变迁。如果发现内部是部分重复，或者完全不重复，即切开不同的输出事件后，
    发现这些输入信号变化是这些输出信号各种的触发，则分别构造不同的变迁。
    （5）针对输入信息为0，但是输出信号不为0的情况，
        第一：假设输出是单一输出，直接向前寻找，找到一个最近的且是当前输出的触发输入时停止（还需要保证此时的输出为0）；
        第二：假设输出是多个输出，需要分别寻找每一个输出的触发输入，如果发现有公共的输入（注意：公共的可能不止有一个），则向前寻找匹配这个公共输入的信号，如果没有公共的输入，则向前寻找最近的其中一个输出的触发输入。
        情况：多个输出的情况下，如果这些输入不存在公共的输入，则说明他们是虚假的并发，应当分别向前寻找这些输出对应的触发输入,方案是向前遍历，和匹配的输出对应的输入进行比较，
        如果发现一致，则构造变迁，然后立即停止（表示这是最近的一个符合其中某个输入的触发函数的信号值）。
        
    
    触发序列中的两个不确定性：
        一个是输入信息为0，但是输出信号不为0的情况中，如果不存在公共的触发函数，则向前寻找最近的其中一个输出的触发函数，这里无法确定匹配的到底是哪个输出的触发函数。
        另一个是多个输出的情况下，如果这些输入不存在公共的输入，则说明他们是虚假的并发，应当分别向前寻找这些输出对应的触发输入,然后构造变迁，这里因为遍历的循序是不确定的，构造变迁的顺序。
        
        
"""

class fireFunction:
    # 构造函数-注意：前面是两条连续的下划线
    def __init__(self, transition, letter_mapping, letter_counter,fix_t=0):
        # 最终的变迁构造
        self.transition = transition
        # 输入信号对应的变迁映射器字典
        self.letter_mapping = letter_mapping
        # 映射器当前长度
        self.letter_counter = letter_counter
        # 关联矩阵
        self.incidence_matrix = pd.DataFrame()
        # 修正过的变迁数量
        self.fix_t = fix_t




    # 用于处理当前输入信号中，输入信号全为0，但是输出信号不全为的情况
    # 参数一：触发函数
    # 参数二：所有信号变化量
    # 参数三：信号中，输入部分的长度
    # 参数四：当前正在遍历的信号变化量的索引
    def  fix_none_input(self,fire_function,signal,input_nums,index):
        item = signal[index]
        input_part = item[:input_nums]  # 输入部分
        output_part = item[input_nums:]  # 输出部分

        # 格式化当前信号的输出部分，和字典中的数据格式一致
        output_str = ' '.join(map(str, output_part))
        # 格式化当前信号的输入部分，和字典中的数据格式一致
        input_str = ' '.join(map(str, input_part))

        # 如果发现当前取出信号的输入部分全为0，且输出部分不全为0，则向前寻找，如果当前输出是当输出，则找到前一个最近的该输出的触发函数
        # 如果当前输出不是单输出，则向前寻找公共的触发函数，如果不存在，则向前找到最近的其中一个输出的触发函数
        # 如果发现前一个事件序列的输入仍然为0，则继续向前寻找，直到找到一个不全为0的输入

        # 解析这个输入为0，但是输出不为0的信号的输出信号值
        all_output = self.find_similar_output(output_str, fire_function)
        # 用于判断是否已经修正了当前输入是0的情况
        hasfix = False
        # 用于记录是否是多输出事件不存在公共的触发函数的分支
        not_common = False
        letter_key = ''
        # 如果发现是多输出信号，需要进行相应的处理
        if len(all_output) > 1:
            # 1、先寻找公共的触发函数
            merged_arrays = list()
            for output in all_output:
                # 遍历每一个匹配的输出信号，把其对应的输入信号list展平成一个字符串，存储到一维数组中
                arrays = fire_function.get(output)
                flatter_array = [' '.join(sublist) for sublist in arrays]
                merged_arrays.append(flatter_array)
            # 找到多个输出对应输入（触发函数）的公共元素
            common = self.find_common_elements(merged_arrays)
            if common and len(common) > 0:
                print("修正过程中发现了公共触发函数：")
                print(common)
                # 由于公共元素可能不止一个，所以这里进行收集
                all_commons = list()
                for com in common:
                    all_commons.append(com.split(' '))
                # 从当前信号开始向前寻找
                hasfix,letter_key = self.look_front_for_transition(signal=signal,input_nums=input_nums,index=index,
                                               match_inputs=all_commons)
            else:
                not_common = True
                # 2、如果没有公共的触发函数，就向前寻找最近的某个输出的触发函数
                # 从当前信号开始向前寻找
                j = index
                print("修正过程中没有发现公共触发函数，向前寻找最近的某个输出的触发函数")
                while j > 0:
                    j -= 1
                    temp = signal[j]
                    input_part = temp[:input_nums]
                    output_part = temp[input_nums:]
                    # 向前寻找的输入，需要保证其输出是空的，这里不使用那些输入和输出均不全是0的有效信号
                    if sum(abs(y) for y in input_part) == 0 or sum(abs(x) for x in output_part) != 0:
                        continue
                    else:
                        # 获取到当前解析的输出对应的触发函数-无噪声输入信号列表
                        # 判断当前信号的输入部分是否在触发函数对应的输入列表中
                        input_str = ' '.join(map(str, input_part))
                        input_val = [x for x in input_str.split(' ') if x != '']
                        # 遍历每一个匹配的输出信号，获取到其对应的输入信号列表，和当前的输入信号进行比较
                        hasfound = []
                        for out in all_output:
                            fire = fire_function.get(out)
                            input_found, input_key = self.find_match(input_val, fire)
                            # 如果找到匹配，则创建字母标记，并添加到变迁中
                            if input_found:
                                hasfound.append(True)
                                key = ' '.join(input_key)
                                if key not in self.letter_mapping:
                                    self.letter_counter += 1
                                    self.letter_mapping[key] = 't' + str(self.letter_counter)
                                    # 构造关联矩阵，添加一列
                                    self.incidence_matrix[len(self.incidence_matrix.columns)] = output_part
                                # 从映射表中获取字母标记
                                letter = self.letter_mapping[key]
                                print(f"数据 {index + 1} 向前找到了对应的字母标记：{letter}，输入部分：{input_str}，输出部分：{output_str}")
                                self.transition += letter + ' '
                                # 修正过的变迁数量加1
                                self.fix_t += 1
                                # 找到一个最近的就跳出循环
                                # break
                            else:
                                pass
                        # 如果均找到了最近的一个触发，则跳出while循环
                        if all(hasfound):
                            break

        # 如果是单输出信号
        elif len(all_output) == 1:
            print("修正过程中是单一输出信号")
            # 从当前信号开始向前寻找，直到找到一个不全为0的输入
            # 获取到当前解析的输出对应的触发函数-无噪声输入信号列表
            inputs = fire_function.get(all_output[0])
            hasfix,letter_key = self.look_front_for_transition(signal=signal, input_nums=input_nums, index=index,
                                           match_inputs=inputs)
        else:
            pass

        # 单输出事件和存在公共触发输入的情况下，判断是否已经修正了输入为0输出不为0的情况，如果仍然没有，则打印结果
        if not not_common:
            if not hasfix:
                print(f"数据 {index + 1} 没有找到匹配的输入输出，输入部分：{input_str}，输出部分：{output_str}")
            else:
                if letter_key != '':
                    key = letter_key
                    if key not in self.letter_mapping:
                        self.letter_counter += 1
                        self.letter_mapping[key] = 't' + str(self.letter_counter)
                        # 构造关联矩阵，添加一列
                        self.incidence_matrix[len(self.incidence_matrix.columns)] = output_part
                    # 从映射表中获取字母标记
                    letter = self.letter_mapping[key]
                    print(f"数据 {index + 1} 向前找到了对应的字母标记（修正）：{letter}，输入部分：{input_str}，输出部分：{output_str}")
                    self.transition += letter + ' '
                    # 修正过的变迁数量加1
                    self.fix_t += 1





    # 向前遍历信号变化量，寻找可行的匹配输入
    # 参数一：所有信号变化量
    # 参数二：信号中输入部分的长度
    # 参数三：当前正在遍历的信号变化量的索引
    # 参数四：匹配的输出中，对应的无噪声输入--输出对应的触发函数
    # 返回值：是否找到匹配的信号，以及匹配的信号对应的字母标记letter_key
    def look_front_for_transition(self,signal,input_nums,index,match_inputs):
        j = index
        # 用于判断是否已经修正了当前输入是0的情况
        hasfix = False
        # 用于记录当前修正后的匹配对应的字母标记
        letter_key = ''
        while j > 0:
            j -= 1
            temp = signal[j]
            input_part = temp[:input_nums]
            output_part = temp[input_nums:]
            # 向前寻找的输入，需要保证其输出是空的，这里不使用那些输入和输出均不全是0的有效信号
            if sum(abs(y) for y in input_part) == 0 or sum(abs(x) for x in output_part) != 0:
                continue
            else:
                # 获取到当前解析的输出对应的触发函数-无噪声输入信号列表
                # 判断当前信号的输入部分是否在触发函数对应的输入列表中
                input_str = ' '.join(map(str, input_part))
                input_val = [x for x in input_str.split(' ') if x != '']
                input_found, input_key = self.find_match(input_val, match_inputs)
                # 如果找到匹配，则创建字母标记，并添加到变迁中
                if input_found:
                    hasfix = True
                    letter_key = ' '.join(input_key)
                    break

        return hasfix,letter_key





    # 遍历信号变化量，构造发射序列
    # 参数一：信号变化量列表
    # 参数二：触发函数
    # 参数三：信号中，输入部分的长度
    def find_transition(self, signal, fire_function, input_nums=17):
        # 遍历二维列表数据
        for i, item in enumerate(signal):
            input_part = item[:input_nums]  # 输入部分
            output_part = item[input_nums:]  # 输出部分

            # 格式化当前信号的输出部分，和字典中的数据格式一致
            output_str = ' '.join(map(str, output_part))
            # 格式化当前信号的输入部分，和字典中的数据格式一致
            input_str = ' '.join(map(str, input_part))
            input_val = [x for x in input_str.split(' ') if x != '']

            # 如果发现当前取出信号的输入部分全为0，且输出部分不全为0，则向前寻找，
            # 如果当前输出是当输出，则找到前一个最近的该输出的触发函数
            # 如果当前输出不是单输出，则向前寻找公共的触发函数，如果不存在，则向前找到最近的其中一个输出的触发函数
            # 如果发现前一个事件序列的输入仍然为0，则继续向前寻找，直到找到一个不全为0的输入
            sum_input = sum(abs(x) for x in input_part)
            sum_output = sum(abs(y) for y in output_part)

            if sum_input == 0 and sum_output != 0:
                self.fix_none_input(fire_function=fire_function,signal=signal,input_nums=input_nums,index=i)
                # 针对输入信息为0，但是输出信号不为0的情况，这里处理完就不需要后续的处理了，直接跳过，到下一个循环
                continue

            # 查找是否有相同的输出
            marked = False
            if fire_function.get(output_str) is not None:
                inputs = fire_function.get(output_str)
                # 如果发现当前信号的输入部分不在触发函数的输入列表中，则说明包含噪声，需要逐个比较对应的非0项所在的位置
                input_found, input_key = self.find_match(input_val, inputs)

                # 如果找到匹配，则创建字母标记，并添加到变迁中
                if input_found:
                    key = ' '.join(input_key)
                    print("单一输出和输入（包括无噪声和有噪声）的key: ")
                    print(key)
                    if key not in self.letter_mapping:
                        self.letter_counter += 1
                        self.letter_mapping[key] = 't' + str(self.letter_counter)
                        # 构造关联矩阵，添加一列
                        self.incidence_matrix[len(self.incidence_matrix.columns)] = output_part
                    # 从映射表中获取字母标记
                    letter = self.letter_mapping[key]
                    marked = True
                    print(f"数据 {i + 1} 对应的字母标记：{letter}，输入部分：{input_str}，输出部分：{output_str}")
                    self.transition += letter + ' '

            # 如果发现触发函数中不存在，则表示当前输出不是单一的1或者-1，需要另外处理，解析其混合的触发函数
            else:
                # 解析出当前输出信号中的非0元素所在的位置，比较fire_function中的输出信号中的非0元素所在的位置，如果发现相同的位置，则认为有同样的输出信号
                # 从fire_function中解析出当前输出信号中的非0元素所在的位置相同的输出信号key
                matching_keys = self.find_similar_output(output_str, fire_function)
                if matching_keys:
                    # 用于记录解析出的不同输出信号匹配的输入信号列表值
                    match_inputs = []
                    # 遍历匹配的输出信号key，匹配当前信号中输入部分对应的无噪声输入信号列表
                    for match_key in matching_keys:
                        # 取出当前匹配的某个输出信号对应的输入列表
                        inputs = fire_function.get(match_key)
                        # 判断当前信号的输入部分是否在触发函数对应的输入列表中
                        input_found, input_key = self.find_match(input_val, inputs)

                        # 如果找到匹配，则创建字母标记，并添加到变迁中
                        if input_found:
                            match_inputs.append(' '.join(input_key))

                    if len(match_inputs) >= 1:
                        print(f"数据 {i + 1} 存在多个输入匹配，输入部分：{input_str}，输出部分：{output_str}")
                        print("混合输出的match_inputs: ")
                        print(self.unique_list(match_inputs))

                        # 如果是多个输入匹配相互之间均是不同的输入信号值，则认为这是一种虚假的同步，分别构造变迁
                        # 如果发现多输入匹配中是部分相同的输入信号值，则认为这是一种并发，构造一个变迁
                        for input in self.unique_list(match_inputs):
                            key = input
                            print("混合输出存在多个匹配输入的key: ")
                            print(key)

                            if key not in self.letter_mapping:
                                self.letter_counter += 1
                                self.letter_mapping[key] = 't' + str(self.letter_counter)
                                # 构造关联矩阵，添加一列
                                self.incidence_matrix[len(self.incidence_matrix.columns)] = output_part
                            # 从映射表中获取字母标记
                            letter = self.letter_mapping[key]
                            marked = True
                            print(f"数据 {i + 1} 对应的字母标记：{letter}，输入部分：{input_str}，输出部分：{output_str}")
                            self.transition += letter + ' '

                    else:
                        # 如果无法找到匹配，则跳过
                        pass

            # 如果没有找到匹配的输出，可以进行相应的处理
            if not marked:
                print(f"数据 {i + 1} 没有找到匹配的输入输出，输入部分：{input_str}，输出部分：{output_str}")

        print("字母映射表：")
        print(self.letter_mapping)
        return self.transition



    # 去除重复的输入字符，如['0 0 -1 0 0 ', '0 0 -1 0 0 ', '0 0 1 0 0 ']
    def unique_list(self,seq_list):
        unique = set()
        unique_list = []
        for sublist_str in seq_list:
            if sublist_str not in unique:
                unique_list.append(sublist_str)
                unique.add(sublist_str)
        return unique_list


    # 解析一个字符串并找到其中非零元素的索引位置的下标
    def find_nonzero_indices(self,s):
        # 解析字符串并找到非零元素的索引位置以及该位置的元素
        elements = s.split()
        nonzero_indices = [(i,element) for i, element in enumerate(elements) if element != '0']
        return nonzero_indices


    # 解析字符串并找到与无噪声输出相同位置非零元素的索引位置
    # 参数一：当前输出信号
    # 参数二：一个字典，其key是不同位置的输出信号，value是对应的输入信号列表
    # 返回值：匹配的输出信号列表
    def find_similar_output(self,current,dictionary):
        # 找到当前输出中非零元素的索引位置以及该位置的元素
        a_indices = self.find_nonzero_indices(current)

        # 在字典中查找与当前输出信号字符非零元素的位置匹配的输出信号
        matching_keys = []
        for key in dictionary.keys():
            value_indices = self.find_nonzero_indices(key)
            #判断当前信号是否在对应位置，即判断value_indices中的元素是否在a_indices中
            if value_indices[0] in a_indices:
                matching_keys.append(key)

        return matching_keys


    # 对比当前信号的输入部分，判断是否在相同的索引位置存在相同的非零元素
    # 参数一：当前信号的输入部分
    # 参数二：触发函数中的无噪声输入信号列表
    def find_match(self,input_val,inputs):
        # 初始化触发函数标志为False
        input_found = False
        # 用于记录匹配的无噪声的输入信号
        input_key = []
        # 遍历匹配的输出信号中对应的输入列表，找到当前信号的匹配输入（即只要保证存在在同一位置有输入信号--其他位置视为噪声）
        for input in inputs:
            match = True
            # 检查是否在相同位置上存在非0的元素
            for j in range(len(input)):
                # 只要发现参照数组上某个元素是非0元素，而当前输入数组中对应位置的元素是0，就说明不匹配
                if input[j] != '0' and input_val[j] == '0':
                    match = False
                    break
                # 如果发现参照数组上某个元素是非0元素，而噪声数组中对应位置的元素也是非0元素，但是两者不相等，也说明不匹配
                if input[j] != '0' and input_val[j] != '0' and input[j] != input_val[j]:
                    match = False
                    break

            if match:
                input_found = True
                input_key = input
                break  # 找到匹配，不再继续搜索

        return input_found,input_key


    # 找到多个一维数组的公共元素
    # 参数: 二维数组列表
    # 返回: 公共元素列表
    # 参数示例：arrays = [
    #         ['0 0 0 0 0 0 0 -1 0', '0 0 0 0 0 1 0 0 0', '1 0 0 0 0 0 0 0 0'],
    #         ['1 0 0 0 0 0 0 0 0','0 0 0 0 0 0 0 -1 0','0 0 0 0 0 1 0 0 0'],
    #         ['0 0 0 0 0 0 0 -1 0','1 0 0 0 0 0 0 0 0']
    #     ]
    def find_common_elements(self,arrays):
        # 创建一个有序的字典集合，用于存储所有数组中的唯一元素
        element_dict = OrderedDict()
        for array in arrays:
            for element in array:
                if element not in element_dict:
                    element_dict[element] = element

        # 找到集合中的所有公共元素
        common_elements = list()
        for element in element_dict.keys():
            if all(element in array for array in arrays):
                common_elements.append(element)

        return common_elements



# 读取csv格式的数据，按照传入的输入和输出信号长度，进行解析，然后转换为excel格式的数据
# 参数一：csv文件名
# 参数二：导出的excel文件名
# 参数三：输入信号长度
# 参数四：输出信号长度
def csv_to_excel(filename,export_name,input_nums=17,output_nums=13):
        # 读取csv格式的数据
        df = pd.read_csv(filename, header=None)

        # 切分输入和输出列
        input_columns = df.iloc[:, :input_nums]
        output_columns = df.iloc[:, input_nums:]

        # 给excel添加列名，规则：输入：‘i+数字’，输出：‘o+数字’
        # 给输入列添加新的列名
        input_column_names = [f'i{i}' for i in range(1, input_nums + 1)]
        input_columns.columns = input_column_names

        # 给输出列添加新的列名
        output_column_names = [f'o{i}' for i in range(1, output_nums + 1)]
        output_columns.columns = output_column_names

        # 将切分后的数据合并
        result_df = pd.concat([input_columns, output_columns], axis=1)

        # 将数据保存为excel格式的数据，不保存索引
        return result_df.to_excel(export_name,index=False)



# 读取excel文件中的二进制信号，计算信号变化量
# 参数：excel文件名称路径
def compute_change_signal(path):
    # 读取Excel文件
    df = pd.read_excel(path)
    # 初始化变化量列表
    differences = []
    # 前一行初始化为excel中数据的第一行
    previous_row = list(df.iloc[0])

    # 从excel第二行开始遍历每一行
    for index, row in df.iloc[1:].iterrows():
        current_row = list(row)
        # 计算当前行和前一行的变化量
        difference = [current - previous for current, previous in zip(current_row, previous_row)]
        # 将变化量添加到列表中
        differences.append(difference)
        # 更新前一行
        previous_row = current_row

    return differences


# 把输出信号转化为“a数字_0/1的形式”
def io_to_fire_string(io_strs):
    result_list = []

    for output_str in io_strs:
        # 按空格切割字符串，并转化为int类型
        numbers = [int(num) for num in output_str.split(" ")]

        # 遍历字符串中的非0元素
        for i, num in enumerate(numbers):
            if num != 0:
                if num == 1:
                    result_list.append(f'a{i + 1}_1')
                else:
                    result_list.append(f'a{i + 1}_0')

    return result_list




# 定义模板流程
# 参数一：csv文件名
# 参数二：导出的excel文件名
# 参数三：输入信号长度
# 参数四：输出信号长度
# 参数五：是否可视化
def main_process(out_excel_name,input_nums,output_nums,visualize=False,csv_data=''):
    # 1、把csv格式的数据转换为excel格式的数据
    if csv_data != '':
        csv_to_excel(filename=csv_data,export_name=out_excel_name,input_nums=input_nums,output_nums=output_nums)

    df = pd.read_excel(out_excel_name)


    # 2、计算信号变化量
    change_list = compute_change_signal(out_excel_name)
    # pd.DataFrame(change_list).to_excel('data/20_diff_change.xlsx',index=False)


    # 3、把信号变化量列表转换为DataFrame形式的数据
    df = pd.DataFrame(change_list,columns=df.columns)
    print(df.head(5))


    # 4、从信号中切分输入和输出，找到不同的输出对应的输入列表（已经去除了重复）
    filter = fns.find_input_of_output(df,input_nums=input_nums,output_nums=output_nums)
    # 创建副本
    before = filter.copy()



    # 5、遍历筛选出的每一个输出信号变化量对应的输入信号变化量列表，找到包含最多0（最少1或-1）的列表，然后从其他列表中删除多余的元素（1或-1）
    result_dict = fns.find_read_input_of_output(filter)



    # 7、从信号中解析出变迁序列
    ff  = fireFunction(transition='',letter_mapping=dict(),letter_counter=0)
    transition = ff.find_transition(change_list, result_dict, input_nums=input_nums)



    # 8、构造关联矩阵，通过关联矩阵计算可观察部分的petri网结构
    print("关联矩阵：")
    print(ff.incidence_matrix)
    incidence = ff.incidence_matrix.values.tolist()
    print(incidence)
    p,t,a = bp.extract_pt_and_relationships(incidence)
    print(p)
    print(t)
    print(a)
    bp.build_petri_net(places=p,transitions=t,arcs=a,visualize=visualize)


    return before,result_dict,transition,ff



# 数据统计
# 参数一：csv文件名
# 参数二：导出的excel文件名
# 参数三：输入信号长度
# 参数四：输出信号长度
# 参数五：是否可视化
def data_Statistics(csv_data='',out_excel_name='', input_nums=17, output_nums=13, visualize=True):
    filter,result_dict,transition,ff = main_process(csv_data=csv_data,out_excel_name=out_excel_name,
                                                    input_nums=input_nums,
                                                    output_nums=output_nums, visualize=visualize)

    print("筛选出不同位置的输出信号对应的输入信号：")
    print(filter)
    before = 0
    before_nums = []
    for key,v in filter.items():
        print(f"输出：{key}，输入：{len(v)}")
        before += len(v)
        before_nums.append(len(v))


    print("过滤噪声后的结果（触发函数值）：")
    print(result_dict)
    after = 0
    after_nums = []
    for key,v in result_dict.items():
        print(f"输出：{key}，输入数量：{len(v)}")
        after += len(v)
        after_nums.append(len(v))


    res_strs = io_to_fire_string(filter.keys())
    print(res_strs)
    print(before_nums)
    print(after_nums)

    # 6、计算过滤噪声前后信号数量减少了多少百分比
    print(f"前{before},后{after},前后之差：{(before - after)}。过滤噪声前后信号数量减少了：{round((before - after) / before * 100, 2)}%")

    gp.draw_plot(res_strs,before_nums,after_nums)

    print("变迁序列：")
    print(transition)

    print("修正过的变迁数量：")
    print(ff.fix_t)





if __name__ == '__main__':

    # data_Statistics(csv_data='',out_excel_name='data/output.xlsx',input_nums=9,output_nums=4,visualize=True)


    data_Statistics(csv_data='',out_excel_name='data/20_diff.xlsx', input_nums=17, output_nums=13, visualize=True)



