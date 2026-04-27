-- 江阴贷款台账合并1 查询索引
-- 在 Oracle 11g 中以 SYSDBA 或有 CREATE INDEX 权限的用户执行

-- 证件号精确匹配索引
CREATE INDEX idx_jydk_zjh ON 江阴贷款台账合并1(证件号);

-- 客户名称前缀匹配索引（支持 LIKE '张三%'）
CREATE INDEX idx_jydk_khmc ON 江阴贷款台账合并1(客户名称);

-- 收集统计信息，让优化器认识索引
BEGIN
  DBMS_STATS.GATHER_TABLE_STATS(USER, '江阴贷款台账合并1', CASCADE => TRUE);
END;
/

-- 如果需要支持中间模糊查询（LIKE '%张三%'），取消下面注释：
-- 前提：Oracle Text 已安装（11g 默认带 CTXSYS.CONTEXT）
-- EXEC CTX_DDL.CREATE_PREFERENCE('JYDK_LEXER', 'CHINESE_VGRAM_LEXER');
-- CREATE INDEX idx_jydk_khmc_ft ON 江阴贷款台账合并1(客户名称)
--   INDEXTYPE IS CTXSYS.CONTEXT
--   PARAMETERS('LEXER JYDK_LEXER SYNC(ON COMMIT)');
