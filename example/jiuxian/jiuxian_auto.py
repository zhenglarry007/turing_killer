#!/usr/bin/env python3
import time
import random
from datetime import datetime

from config import EXECUTE_COUNT
from browser_layer import create_driver
from business_layer import jiuxian_send


def main():
    execute_count = EXECUTE_COUNT
    
    print(f"开始执行酒仙网自动化任务，执行次数: {execute_count} 次")
    
    driver = create_driver()
    
    try:
        for i in range(execute_count):
            current_round = i + 1
            
            print(f"\n{'='*60}")
            print(f"第 {current_round}/{execute_count} 次执行")
            print(f"{'='*60}")
            print(f"执行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            
            phone_prefixes = ["131", "132", "133", "135", "136", "137", "138", "139", "150", "151", "152", "153", "155", "156", "157", "158", "159", "186", "187", "188", "189"]
            random_prefix = random.choice(phone_prefixes)
            random_suffix = "".join([str(random.randint(0, 9)) for _ in range(8)])
            random_phone = f"{random_prefix}{random_suffix}"
            
            result = jiuxian_send(driver, "62", random_phone)
            
            if result:
                print(f"执行结果: ret={result.ret}, msg={result.msg}")
            else:
                print(f"执行结果: 失败")
            
            time.sleep(2)
        
        print(f"\n{'='*60}")
        print(f"任务完成！共执行 {execute_count} 次")
        print(f"{'='*60}")
            
    finally:
        print("正在关闭浏览器...")
        driver.quit()


if __name__ == "__main__":
    main()
