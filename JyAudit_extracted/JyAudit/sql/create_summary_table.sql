-- ============================================
-- 江阴时点贷款汇总表
-- 按客户 + 年末时点汇总各年度借据余额
-- 日期字段为 NUMBER(8) 格式：YYYYMMDD（如 20110330）
-- ============================================

-- 1. 删旧表（如果存在）
DROP TABLE 江阴时点贷款汇总表 PURGE;

-- 2. 建表：一次全表扫描 + CASE WHEN 交叉汇总
--    YYYYMMDD 格式直接用数字比较，无需 TO_DATE 转换
--    结清日期 = 0 表示未结清
CREATE TABLE 江阴时点贷款汇总表 AS
SELECT
  客户名称,
  证件号 AS 证件号码,
  SUM(CASE
    WHEN 放款日期 <= 20221231
     AND (结清日期 IS NULL OR 结清日期 = 0 OR 结清日期 > 20221231)
    THEN 借据余额 ELSE 0
  END) AS Y2022,
  SUM(CASE
    WHEN 放款日期 <= 20231231
     AND (结清日期 IS NULL OR 结清日期 = 0 OR 结清日期 > 20231231)
    THEN 借据余额 ELSE 0
  END) AS Y2023,
  SUM(CASE
    WHEN 放款日期 <= 20241231
     AND (结清日期 IS NULL OR 结清日期 = 0 OR 结清日期 > 20241231)
    THEN 借据余额 ELSE 0
  END) AS Y2024,
  SUM(CASE
    WHEN 放款日期 <= 20251231
     AND (结清日期 IS NULL OR 结清日期 = 0 OR 结清日期 > 20251231)
    THEN 借据余额 ELSE 0
  END) AS Y2025,
  SUM(CASE
    WHEN 放款日期 <= 20261231
     AND (结清日期 IS NULL OR 结清日期 = 0 OR 结清日期 > 20261231)
    THEN 借据余额 ELSE 0
  END) AS Y2026
FROM 江阴贷款台账合并1
GROUP BY 客户名称, 证件号;

-- 3. 索引
CREATE INDEX idx_hzb_zjh ON 江阴时点贷款汇总表(证件号码);
CREATE INDEX idx_hzb_khmc ON 江阴时点贷款汇总表(客户名称);

-- 4. 统计信息
BEGIN
  DBMS_STATS.GATHER_TABLE_STATS(USER, '江阴时点贷款汇总表', CASCADE => TRUE);
END;
/
