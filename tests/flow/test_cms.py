
from common import *
from random import randint


class testCMS():
    def __init__(self):
        self.env = Env(decodeResponses=True)
        self.assertOk = self.env.assertTrue
        self.cmd = self.env.cmd
        self.assertEqual = self.env.assertEqual
        self.assertRaises = self.env.assertRaises
        self.assertTrue = self.env.assertTrue
        self.assertAlmostEqual = self.env.assertAlmostEqual
        self.assertGreater = self.env.assertGreater

    def test_simple(self):
        self.cmd('FLUSHALL')
        self.assertOk(self.cmd('cms.initbydim', 'cms1', '20', '5'))
        self.assertEqual([5], self.cmd('cms.incrby', 'cms1', 'a', '5'))
        self.assertEqual([5], self.cmd('cms.query', 'cms1', 'a'))
        self.assertEqual(['width', 20, 'depth', 5, 'count', 5],
                         self.cmd('cms.info', 'cms1'))

        self.assertOk(self.cmd('cms.initbyprob', 'cms2', '0.001', '0.01'))
        self.assertEqual([5], self.cmd('cms.incrby', 'cms2', 'a', '5'))
        self.assertEqual([5], self.cmd('cms.query', 'cms2', 'a'))
        self.assertEqual(['width', 2000, 'depth', 7, 'count', 5],
                         self.cmd('cms.info', 'cms2'))
        yield 1
        self.env.dumpAndReload()
        yield 2
        if not VALGRIND:
            if server_version_at_least(self.env, '7.0.0'):
                self.assertEqual(856, self.cmd('MEMORY USAGE', 'cms1'))
            else:
                self.assertEqual(840, self.cmd('MEMORY USAGE', 'cms1'))

    def test_validation(self):
        self.cmd('FLUSHALL')
        for args in (
                (),
                ('foo',),
                ('foo', '0.1'),
                ('foo', '0.1', 'blah'),
                ('foo', '10'),
                ('foo', '10', 'blah'),
                ('foo', 'blah', '10'),
                ('foo', '0', '0'),
                ('foo', '0', '100'),
                ('foo', '100', '0'),
        ):
            self.assertRaises(ResponseError, self.cmd, 'cms.initbydim', *args)

        for args in (
                (),
                ('foo',),
                ('foo', '1000'),
                ('foo', '0.1'),
                ('foo', '1000', '0.1'),
                ('foo', '1000', 'blah'),
                ('foo', '1000', '10'),
                ('foo', '0.1', 'blah'),
                ('foo', '10', 'blah'),
                ('foo', 'blah', '10'),
                ('foo', '0', '0'),
                ('foo', '1000', '0',),
                ('foo', '0', '100'),
        ):
            self.assertRaises(ResponseError, self.cmd, 'cms.initbyprob', *args)

        self.assertRaises(ResponseError, self.cmd, 'cms.initbydim', '0.1', '0.1')
        self.assertRaises(ResponseError, self.cmd, 'cms.initbyprob', '10', '10')

        self.assertOk(self.cmd('cms.initbydim', 'testDim', '100', '5'))
        self.assertOk(self.cmd('cms.initbyprob', 'testProb', '0.1', '0.1'))

        for args in ((), ('test',)):
            for cmd in ('cms.incrby', 'cms.query', 'cms.merge', 'cms.info'):
                self.assertRaises(ResponseError, self.cmd, cmd, *args)

    def test_incrby_query(self):
        self.cmd('FLUSHALL')
        self.cmd('SET', 'A', 'B')
        self.cmd('cms.initbydim', 'cms', '1000', '5')
        self.cmd('cms.incrby', 'cms', 'bar', '5', 'baz', '42')
        self.assertEqual([0], self.cmd('cms.query', 'cms', 'foo'))
        self.assertEqual([0, 5, 42], self.cmd('cms.query',
                                              'cms', 'foo', 'bar', 'baz'))
        self.assertRaises(ResponseError, self.cmd, 'cms.incrby', 'noexist', 'bar', '5')
        self.assertRaises(ResponseError, self.cmd, 'cms.incrby', 'A', 'bar', '5')
        self.assertRaises(ResponseError, self.cmd, 'cms.incrby',
                          'cms', 'bar', '5', 'baz')
        self.assertRaises(ResponseError, self.cmd, 'cms.incrby',
                          'cms', 'bar', '5', 'baz')
        self.assertEqual([0, 5, 42], self.cmd('cms.query',
                                              'cms', 'foo', 'bar', 'baz'))

        # c = self.client
        self.cmd('cms.initbydim', 'test', '1000', '5')
        self.assertEqual([1], self.cmd('cms.incrby', 'test', 'foo', '1'))
        self.assertEqual([1], self.cmd('cms.query', 'test', 'foo'))
        self.assertEqual([0], self.cmd('cms.query', 'test', 'bar'))

        self.assertEqual([2, 1], self.cmd('cms.incrby', 'test', 'foo', '1', 'bar', '1'))
        # for _ in c.retry_with_rdb_reload():
        #     self.assertEqual([2], self.cmd('cms.query', 'test', 'foo'))
        #     self.assertEqual([1], self.cmd('cms.query', 'test', 'bar'))
        #     self.assertEqual([0], self.cmd('cms.query', 'test', 'nonexist'))

    def test_merge(self):
        self.cmd('FLUSHALL')
        self.cmd('cms.initbydim', 'small_1{1}', '20', '5')
        self.cmd('cms.initbydim', 'small_2{1}', '20', '5')
        self.cmd('cms.initbydim', 'small_3{1}', '20', '5')
        self.cmd('cms.initbydim', 'large_4{1}', '2000', '10')
        self.cmd('cms.initbydim', 'large_5{1}', '2000', '10')
        self.cmd('cms.initbydim', 'large_6{1}', '2000', '10')

        # empty small batch
        self.assertOk(self.cmd('cms.merge', 'small_3{1}', 2, 'small_1{1}', 'small_2{1}'))
        self.assertEqual(['width', 20, 'depth', 5, 'count', 0],
                         self.cmd('cms.info', 'small_3{1}'))

        # empty large batch
        self.assertOk(self.cmd('cms.merge', 'large_6{1}', 2, 'large_4{1}', 'large_5{1}'))
        self.assertEqual(['width', 2000, 'depth', 10, 'count', 0],
                         self.cmd('cms.info', 'large_6{1}'))

        # non-empty small batch
        self.cmd('cms.incrby', 'small_1{1}', 'a', '21')
        self.cmd('cms.incrby', 'small_2{1}', 'a', '21')
        self.assertOk(self.cmd('cms.merge', 'small_3{1}', 2, 'small_1{1}', 'small_2{1}'))
        self.assertEqual([42], self.cmd('cms.query', 'small_3{1}', 'a'))

        # non-empty small batch
        self.cmd('cms.incrby', 'large_4{1}', 'a', '21')
        self.cmd('cms.incrby', 'large_5{1}', 'a', '21')
        self.assertOk(self.cmd('cms.merge', 'large_6{1}', 2, 'large_4{1}', 'large_5{1}'))
        self.assertEqual([42], self.cmd('cms.query', 'large_6{1}', 'a'))

        # mixed batch
        self.assertRaises(ResponseError, self.cmd, 'cms.merge', 'small_3{1}', 2,
                          'small_2{1}', 'large_5{1}')

    def test_errors(self):
        self.cmd('FLUSHALL')
        self.cmd('SET', 'A', '2000')
        self.assertRaises(ResponseError, self.cmd, 'cms.initbydim', 'A', '2000', '10')
        self.assertRaises(ResponseError, self.cmd, 'cms.incrby', 'A', 'foo')
        self.assertRaises(ResponseError, self.cmd, 'cms.incrby', 'B', '5')
        self.assertRaises(ResponseError, self.cmd, 'cms.info', 'A')

        self.assertOk(self.cmd('cms.initbydim', 'foo', '2000', '10'))
        self.assertOk(self.cmd('cms.initbydim', 'bar', '2000', '10'))
        self.assertOk(self.cmd('cms.initbydim', 'baz', '2000', '10'))
        self.assertRaises(ResponseError, self.cmd, 'cms.incrby', 'foo', 'item', 'foo')
        self.assertRaises(ResponseError, self.cmd, 'cms.incrby', 'foo', 'item', '-1')
        self.assertRaises(ResponseError, self.cmd, 'cms.merge', 'foo', 2, 'foo')
        self.assertRaises(ResponseError, self.cmd, 'cms.merge', 'foo', 'B', 3, 'foo')
        self.assertRaises(ResponseError, self.cmd, 'cms.merge', 'foo', 1, 'bar', 'weights', 'B')
        self.assertRaises(ResponseError, self.cmd, 'cms.merge', 'foo', 3, 'foo', 'weights', 'B')
        self.assertRaises(ResponseError, self.cmd, 'cms.merge', 'foo', 'A', 'foo', 'weights', 1)
        self.assertRaises(ResponseError, self.cmd, 'cms.merge', 'foo', 3, 'bar', 'baz' 'weights', 1, 'a')

    def test_merge_extensive(self):
        self.cmd('FLUSHALL')
        self.cmd('cms.initbydim', 'A{1}', '2000', '10')
        self.cmd('cms.initbydim', 'B{1}', '2000', '10')
        self.cmd('cms.initbydim', 'C{1}', '2000', '10')

        itemsA = []
        itemsB = []
        for i in range(10000):
            itemsA.append(randint(0, 100))
            self.cmd('cms.incrby', 'A{1}', str(i), itemsA[i])
            itemsB.append(randint(0, 100))
            self.cmd('cms.incrby', 'B{1}', str(i), itemsB[i])
        self.assertOk(self.cmd('cms.merge', 'C{1}', 2, 'A{1}', 'B{1}'))

    def test_overflow(self):
        large_val = 1024*1024*1024*2 - 1

        self.cmd('FLUSHALL')
        self.cmd('cms.initbydim', 'cms', '5', '2')
        self.assertEqual([large_val, 10, 17, 5], self.cmd('cms.incrby', 'cms', 'a', large_val, 'b', 10, 'c', 7, 'd', 5))
        self.assertEqual([large_val, 17, 17, 5], self.cmd('cms.query', 'cms', 'a', 'b', 'c', 'd'))
        self.assertEqual([large_val * 2, 27, 34, 10], self.cmd('cms.incrby', 'cms', 'a', large_val, 'b', 10, 'c', 7, 'd', 5))
        self.assertEqual([large_val * 2, 34, 34, 10], self.cmd('cms.query', 'cms', 'a', 'b', 'c', 'd'))

        # overflow as result > UNIT32_MAX
        res = self.cmd('cms.incrby', 'cms', 'a', large_val, 'b', 10, 'c', 7, 'd', 5)
        # result of insert is an error message
        self.env.assertResponseError(res[0], contained='CMS: INCRBY overflow')
        self.assertEqual(res[1:], [44, 51, 15])
        # result of query in UINT32_MAX (large_val * 2 + 1)
        self.assertEqual([large_val * 2 + 1, 51, 51, 15], self.cmd('cms.query', 'cms', 'a', 'b', 'c', 'd'))

    def test_smallset(self):
        self.cmd('FLUSHALL')
        self.assertOk(self.cmd('cms.initbydim', 'cms1', '2', '2'))
        self.assertEqual([10, 42], self.cmd('cms.incrby', 'cms1', 'foo', '10', 'bar', '42'))
        self.assertEqual([10, 42], self.cmd('cms.query', 'cms1', 'foo', 'bar'))
        self.assertEqual(['width', 2, 'depth', 2, 'count', 52],
                         self.cmd('cms.info', 'cms1'))
        self.assertEqual([10, 42], self.cmd('cms.incrby', 'cms1', 'foo', '0', 'bar', '0'))
