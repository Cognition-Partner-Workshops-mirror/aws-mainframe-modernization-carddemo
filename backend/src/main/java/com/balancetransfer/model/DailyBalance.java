package com.balancetransfer.model;

import jakarta.persistence.*;
import java.io.Serializable;
import java.math.BigDecimal;
import java.time.LocalDateTime;

/**
 * Entity representing a single row in the DAILY_BALANCES table.
 * Each record stores daily balance amounts (Day 0 through Day 31)
 * identified by up to 16 configurable keys and a year/month.
 */
@Entity
@Table(name = "DAILY_BALANCES")
public class DailyBalance implements Serializable {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    @Column(name = "BALANCE_ID")
    private Long balanceId;

    @Column(name = "KEY_1", nullable = false, length = 100)
    private String key1;

    @Column(name = "KEY_2", length = 100)
    private String key2;

    @Column(name = "KEY_3", length = 100)
    private String key3;

    @Column(name = "KEY_4", length = 100)
    private String key4;

    @Column(name = "KEY_5", length = 100)
    private String key5;

    @Column(name = "KEY_6", length = 100)
    private String key6;

    @Column(name = "KEY_7", length = 100)
    private String key7;

    @Column(name = "KEY_8", length = 100)
    private String key8;

    @Column(name = "KEY_9", length = 100)
    private String key9;

    @Column(name = "KEY_10", length = 100)
    private String key10;

    @Column(name = "KEY_11", length = 100)
    private String key11;

    @Column(name = "KEY_12", length = 100)
    private String key12;

    @Column(name = "KEY_13", length = 100)
    private String key13;

    @Column(name = "KEY_14", length = 100)
    private String key14;

    @Column(name = "KEY_15", length = 100)
    private String key15;

    @Column(name = "KEY_16", length = 100)
    private String key16;

    @Column(name = "BALANCE_YEAR", nullable = false)
    private Integer balanceYear;

    @Column(name = "BALANCE_MONTH", nullable = false)
    private Integer balanceMonth;

    @Column(name = "DAY_0_BALANCE", precision = 18, scale = 2)
    private BigDecimal day0Balance;

    @Column(name = "DAY_1_BALANCE", precision = 18, scale = 2)
    private BigDecimal day1Balance;

    @Column(name = "DAY_2_BALANCE", precision = 18, scale = 2)
    private BigDecimal day2Balance;

    @Column(name = "DAY_3_BALANCE", precision = 18, scale = 2)
    private BigDecimal day3Balance;

    @Column(name = "DAY_4_BALANCE", precision = 18, scale = 2)
    private BigDecimal day4Balance;

    @Column(name = "DAY_5_BALANCE", precision = 18, scale = 2)
    private BigDecimal day5Balance;

    @Column(name = "DAY_6_BALANCE", precision = 18, scale = 2)
    private BigDecimal day6Balance;

    @Column(name = "DAY_7_BALANCE", precision = 18, scale = 2)
    private BigDecimal day7Balance;

    @Column(name = "DAY_8_BALANCE", precision = 18, scale = 2)
    private BigDecimal day8Balance;

    @Column(name = "DAY_9_BALANCE", precision = 18, scale = 2)
    private BigDecimal day9Balance;

    @Column(name = "DAY_10_BALANCE", precision = 18, scale = 2)
    private BigDecimal day10Balance;

    @Column(name = "DAY_11_BALANCE", precision = 18, scale = 2)
    private BigDecimal day11Balance;

    @Column(name = "DAY_12_BALANCE", precision = 18, scale = 2)
    private BigDecimal day12Balance;

    @Column(name = "DAY_13_BALANCE", precision = 18, scale = 2)
    private BigDecimal day13Balance;

    @Column(name = "DAY_14_BALANCE", precision = 18, scale = 2)
    private BigDecimal day14Balance;

    @Column(name = "DAY_15_BALANCE", precision = 18, scale = 2)
    private BigDecimal day15Balance;

    @Column(name = "DAY_16_BALANCE", precision = 18, scale = 2)
    private BigDecimal day16Balance;

    @Column(name = "DAY_17_BALANCE", precision = 18, scale = 2)
    private BigDecimal day17Balance;

    @Column(name = "DAY_18_BALANCE", precision = 18, scale = 2)
    private BigDecimal day18Balance;

    @Column(name = "DAY_19_BALANCE", precision = 18, scale = 2)
    private BigDecimal day19Balance;

    @Column(name = "DAY_20_BALANCE", precision = 18, scale = 2)
    private BigDecimal day20Balance;

    @Column(name = "DAY_21_BALANCE", precision = 18, scale = 2)
    private BigDecimal day21Balance;

    @Column(name = "DAY_22_BALANCE", precision = 18, scale = 2)
    private BigDecimal day22Balance;

    @Column(name = "DAY_23_BALANCE", precision = 18, scale = 2)
    private BigDecimal day23Balance;

    @Column(name = "DAY_24_BALANCE", precision = 18, scale = 2)
    private BigDecimal day24Balance;

    @Column(name = "DAY_25_BALANCE", precision = 18, scale = 2)
    private BigDecimal day25Balance;

    @Column(name = "DAY_26_BALANCE", precision = 18, scale = 2)
    private BigDecimal day26Balance;

    @Column(name = "DAY_27_BALANCE", precision = 18, scale = 2)
    private BigDecimal day27Balance;

    @Column(name = "DAY_28_BALANCE", precision = 18, scale = 2)
    private BigDecimal day28Balance;

    @Column(name = "DAY_29_BALANCE", precision = 18, scale = 2)
    private BigDecimal day29Balance;

    @Column(name = "DAY_30_BALANCE", precision = 18, scale = 2)
    private BigDecimal day30Balance;

    @Column(name = "DAY_31_BALANCE", precision = 18, scale = 2)
    private BigDecimal day31Balance;

    @Column(name = "CREATED_DATE")
    private LocalDateTime createdDate;

    @Column(name = "UPDATED_DATE")
    private LocalDateTime updatedDate;

    public DailyBalance() {}

    // Getters and setters
    public Long getBalanceId() { return balanceId; }
    public void setBalanceId(Long balanceId) { this.balanceId = balanceId; }

    public String getKey1() { return key1; }
    public void setKey1(String key1) { this.key1 = key1; }

    public String getKey2() { return key2; }
    public void setKey2(String key2) { this.key2 = key2; }

    public String getKey3() { return key3; }
    public void setKey3(String key3) { this.key3 = key3; }

    public String getKey4() { return key4; }
    public void setKey4(String key4) { this.key4 = key4; }

    public String getKey5() { return key5; }
    public void setKey5(String key5) { this.key5 = key5; }

    public String getKey6() { return key6; }
    public void setKey6(String key6) { this.key6 = key6; }

    public String getKey7() { return key7; }
    public void setKey7(String key7) { this.key7 = key7; }

    public String getKey8() { return key8; }
    public void setKey8(String key8) { this.key8 = key8; }

    public String getKey9() { return key9; }
    public void setKey9(String key9) { this.key9 = key9; }

    public String getKey10() { return key10; }
    public void setKey10(String key10) { this.key10 = key10; }

    public String getKey11() { return key11; }
    public void setKey11(String key11) { this.key11 = key11; }

    public String getKey12() { return key12; }
    public void setKey12(String key12) { this.key12 = key12; }

    public String getKey13() { return key13; }
    public void setKey13(String key13) { this.key13 = key13; }

    public String getKey14() { return key14; }
    public void setKey14(String key14) { this.key14 = key14; }

    public String getKey15() { return key15; }
    public void setKey15(String key15) { this.key15 = key15; }

    public String getKey16() { return key16; }
    public void setKey16(String key16) { this.key16 = key16; }

    public Integer getBalanceYear() { return balanceYear; }
    public void setBalanceYear(Integer balanceYear) { this.balanceYear = balanceYear; }

    public Integer getBalanceMonth() { return balanceMonth; }
    public void setBalanceMonth(Integer balanceMonth) { this.balanceMonth = balanceMonth; }

    public BigDecimal getDay0Balance() { return day0Balance; }
    public void setDay0Balance(BigDecimal day0Balance) { this.day0Balance = day0Balance; }

    public BigDecimal getDay1Balance() { return day1Balance; }
    public void setDay1Balance(BigDecimal day1Balance) { this.day1Balance = day1Balance; }

    public BigDecimal getDay2Balance() { return day2Balance; }
    public void setDay2Balance(BigDecimal day2Balance) { this.day2Balance = day2Balance; }

    public BigDecimal getDay3Balance() { return day3Balance; }
    public void setDay3Balance(BigDecimal day3Balance) { this.day3Balance = day3Balance; }

    public BigDecimal getDay4Balance() { return day4Balance; }
    public void setDay4Balance(BigDecimal day4Balance) { this.day4Balance = day4Balance; }

    public BigDecimal getDay5Balance() { return day5Balance; }
    public void setDay5Balance(BigDecimal day5Balance) { this.day5Balance = day5Balance; }

    public BigDecimal getDay6Balance() { return day6Balance; }
    public void setDay6Balance(BigDecimal day6Balance) { this.day6Balance = day6Balance; }

    public BigDecimal getDay7Balance() { return day7Balance; }
    public void setDay7Balance(BigDecimal day7Balance) { this.day7Balance = day7Balance; }

    public BigDecimal getDay8Balance() { return day8Balance; }
    public void setDay8Balance(BigDecimal day8Balance) { this.day8Balance = day8Balance; }

    public BigDecimal getDay9Balance() { return day9Balance; }
    public void setDay9Balance(BigDecimal day9Balance) { this.day9Balance = day9Balance; }

    public BigDecimal getDay10Balance() { return day10Balance; }
    public void setDay10Balance(BigDecimal day10Balance) { this.day10Balance = day10Balance; }

    public BigDecimal getDay11Balance() { return day11Balance; }
    public void setDay11Balance(BigDecimal day11Balance) { this.day11Balance = day11Balance; }

    public BigDecimal getDay12Balance() { return day12Balance; }
    public void setDay12Balance(BigDecimal day12Balance) { this.day12Balance = day12Balance; }

    public BigDecimal getDay13Balance() { return day13Balance; }
    public void setDay13Balance(BigDecimal day13Balance) { this.day13Balance = day13Balance; }

    public BigDecimal getDay14Balance() { return day14Balance; }
    public void setDay14Balance(BigDecimal day14Balance) { this.day14Balance = day14Balance; }

    public BigDecimal getDay15Balance() { return day15Balance; }
    public void setDay15Balance(BigDecimal day15Balance) { this.day15Balance = day15Balance; }

    public BigDecimal getDay16Balance() { return day16Balance; }
    public void setDay16Balance(BigDecimal day16Balance) { this.day16Balance = day16Balance; }

    public BigDecimal getDay17Balance() { return day17Balance; }
    public void setDay17Balance(BigDecimal day17Balance) { this.day17Balance = day17Balance; }

    public BigDecimal getDay18Balance() { return day18Balance; }
    public void setDay18Balance(BigDecimal day18Balance) { this.day18Balance = day18Balance; }

    public BigDecimal getDay19Balance() { return day19Balance; }
    public void setDay19Balance(BigDecimal day19Balance) { this.day19Balance = day19Balance; }

    public BigDecimal getDay20Balance() { return day20Balance; }
    public void setDay20Balance(BigDecimal day20Balance) { this.day20Balance = day20Balance; }

    public BigDecimal getDay21Balance() { return day21Balance; }
    public void setDay21Balance(BigDecimal day21Balance) { this.day21Balance = day21Balance; }

    public BigDecimal getDay22Balance() { return day22Balance; }
    public void setDay22Balance(BigDecimal day22Balance) { this.day22Balance = day22Balance; }

    public BigDecimal getDay23Balance() { return day23Balance; }
    public void setDay23Balance(BigDecimal day23Balance) { this.day23Balance = day23Balance; }

    public BigDecimal getDay24Balance() { return day24Balance; }
    public void setDay24Balance(BigDecimal day24Balance) { this.day24Balance = day24Balance; }

    public BigDecimal getDay25Balance() { return day25Balance; }
    public void setDay25Balance(BigDecimal day25Balance) { this.day25Balance = day25Balance; }

    public BigDecimal getDay26Balance() { return day26Balance; }
    public void setDay26Balance(BigDecimal day26Balance) { this.day26Balance = day26Balance; }

    public BigDecimal getDay27Balance() { return day27Balance; }
    public void setDay27Balance(BigDecimal day27Balance) { this.day27Balance = day27Balance; }

    public BigDecimal getDay28Balance() { return day28Balance; }
    public void setDay28Balance(BigDecimal day28Balance) { this.day28Balance = day28Balance; }

    public BigDecimal getDay29Balance() { return day29Balance; }
    public void setDay29Balance(BigDecimal day29Balance) { this.day29Balance = day29Balance; }

    public BigDecimal getDay30Balance() { return day30Balance; }
    public void setDay30Balance(BigDecimal day30Balance) { this.day30Balance = day30Balance; }

    public BigDecimal getDay31Balance() { return day31Balance; }
    public void setDay31Balance(BigDecimal day31Balance) { this.day31Balance = day31Balance; }

    public LocalDateTime getCreatedDate() { return createdDate; }
    public void setCreatedDate(LocalDateTime createdDate) { this.createdDate = createdDate; }

    public LocalDateTime getUpdatedDate() { return updatedDate; }
    public void setUpdatedDate(LocalDateTime updatedDate) { this.updatedDate = updatedDate; }
}
